from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy import select

from app.db.session import Base, SessionLocal, engine
from app.models.entities import ImageAsset, RenderJob, Scene, Shot
from app.services import messages
from app.services.geometry_backend import (
    GeometryError,
    GeometryQualityRejected,
    GeometryUnavailable,
    get_geometry_backend,
)
from app.services.queue import pop_render
from app.services.renderer import (
    GeometryPathRejected,
    concatenate_timeline,
    geometry_capability_reason,
    render_geometry_motion,
    render_safe_motion,
)
from app.services.scenes import (
    apply_reconstruction_rejection,
    apply_reconstruction_success,
    mark_reconstruction_failed,
    scene_asset_paths,
    scene_workdir,
    select_scene_for_shot,
)
from app.services.storage import storage


def claim_fallback_job() -> str | None:
    with SessionLocal() as db:
        job = db.scalars(select(RenderJob).where(RenderJob.status == "queued").order_by(RenderJob.created_at)).first()
        return job.id if job else None


def process(job_id: str) -> None:
    """Run one job. Reconstruction and rendering share the RenderJob lifecycle."""
    with SessionLocal() as db:
        job = db.get(RenderJob, job_id)
        if not job or job.status not in {"queued", "retry_wait"}:
            return
        job.status = "processing"; job.progress = 0.02; db.commit()

        def progress(value: float, message: str):
            db.expire(job)
            job.progress = max(job.progress, min(1.0, value))
            job.provenance = {**(job.provenance or {}), "last_message": message}
            db.commit()

        def cancelled() -> bool:
            db.refresh(job)
            return bool(job.cancel_requested)

        try:
            if job.type == "reconstruction":
                _process_reconstruction(db, job, progress)
            elif job.type == "timeline":
                _process_timeline_render(db, job, progress, cancelled)
            else:
                _process_render(db, job, progress, cancelled)
        except InterruptedError as e:
            job.status = "cancelled"; job.error = str(e); db.commit()
        except Exception as e:  # noqa: BLE001 — every failure must stay observable
            job.status = "failed"; job.error = str(e); db.commit()


# --------------------------------------------------------------------------- #
# Pipeline 3 — camera reconstruction (COLMAP)
# --------------------------------------------------------------------------- #
def _process_reconstruction(db, job: RenderJob, progress) -> None:
    scene_id = (job.provenance or {}).get("scene_id")
    scene = db.get(Scene, scene_id) if scene_id else None
    if scene is None:
        job.status = "failed"; job.error = "scene not found for this reconstruction job"
        db.commit()
        return

    image_paths = scene_asset_paths(db, scene)
    if not image_paths:
        mark_reconstruction_failed(scene, "scene has no uploaded images")
        job.status = "failed"; job.error = "scene has no uploaded images"; db.commit()
        return

    scene.reconstruction_status = "running"
    db.commit()
    backend = get_geometry_backend()
    workdir = scene_workdir(scene)
    progress(0.05, f"Reconstructing {len(image_paths)} images with COLMAP")

    try:
        result = backend.reconstruct(image_paths, workdir, expected_image_count=len(image_paths))
    except GeometryQualityRejected as exc:
        apply_reconstruction_rejection(scene, exc)
        job.status = "failed"
        job.error = messages.INSUFFICIENT_OVERLAP + " Reasons: " + "; ".join(exc.reasons)
        job.provenance = {
            **(job.provenance or {}),
            "scene": scene.diagnostics,
            "rejection_reasons": exc.reasons,
        }
        db.commit()
        return
    except (GeometryUnavailable, GeometryError) as exc:
        mark_reconstruction_failed(scene, str(exc))
        job.status = "failed"; job.error = str(exc); db.commit()
        return

    apply_reconstruction_success(scene, result)
    job.output_uri = scene.representation_uri
    job.progress = 1.0
    job.status = "completed"
    job.error = None
    job.provenance = {
        **(job.provenance or {}),
        "scene": result.metadata,
        "scene_uri": scene.representation_uri,
        "backend": result.backend,
        "backend_version": result.backend_version,
        "registered_image_ratio": result.registered_image_ratio,
        "camera_count": result.camera_count,
        "geometry_confidence": result.metadata.get("geometry_confidence"),
    }
    db.commit()


# --------------------------------------------------------------------------- #
# Pipeline 5 — preview / final render (geometry when possible, 2.5D otherwise)
# --------------------------------------------------------------------------- #
def _process_render(db, job: RenderJob, progress, cancelled) -> None:
    shot = db.get(Shot, job.shot_id) if job.shot_id else None
    if not shot:
        job.status = "failed"; job.error = "shot not found"; db.commit(); return

    assets = list(db.scalars(select(ImageAsset).where(ImageAsset.id.in_(shot.asset_ids))))
    by_id = {a.id: a for a in assets}
    ordered = [by_id[x] for x in shot.asset_ids if x in by_id]
    image_paths = [storage.resolve(a.storage_uri) for a in ordered]
    out_rel = f"projects/{job.project_id}/renders/{job.id}.mp4"
    out_path = settings_path(out_rel)
    job.provenance = {
        **(job.provenance or {}),
        "requested_mode": job.mode,
        "input_asset_hashes": [a.sha256 for a in ordered],
        "render_config": {
            "mode": job.mode, "width": job.width, "height": job.height,
            "fps": job.fps, "duration_sec": shot.duration_sec, "easing": shot.easing,
        },
    }
    db.commit()

    meta = None
    fallback_reason = None
    if job.mode == "geometry":
        meta, fallback_reason = _try_geometry_render(db, job, shot, out_path, progress, cancelled)

    if meta is None:
        if fallback_reason:
            # Fallback is explicit and observable — never a silent fake (SKILL #35).
            job.provenance = {
                **(job.provenance or {}),
                "fallback_reason": fallback_reason,
                "effective_mode": "2.5d_lite",
            }
            db.commit()
        meta = render_safe_motion(
            image_paths=image_paths,
            output=out_path,
            duration_sec=shot.duration_sec,
            fps=job.fps,
            width=job.width,
            height=job.height,
            progress=progress,
            cancelled=cancelled,
            overlay_title=shot.overlay_title,
            subtitle_text=shot.subtitle_text,
        )

    if cancelled():
        job.status = "cancelled"; db.commit(); return
    job.output_uri = f"local://{out_rel}"
    job.provenance = {**(job.provenance or {}), **meta}
    job.progress = 1.0; job.status = "completed"; job.error = None
    db.commit()


def _try_geometry_render(db, job: RenderJob, shot: Shot, out_path: Path, progress, cancelled):
    """Attempt Geometry Mode; return ``(metadata, fallback_reason)``."""
    scene = select_scene_for_shot(db, shot)
    if scene is None or scene.representation_uri is None:
        return None, messages.SCENE_NOT_RECONSTRUCTED
    if scene.reconstruction_status == "rejected":
        return None, messages.SCENE_REJECTED
    if scene.reconstruction_status != "ready":
        return None, messages.SCENE_NOT_RECONSTRUCTED

    reason = geometry_capability_reason()
    if reason:
        return None, reason

    backend = get_geometry_backend()
    scene_uri = storage.resolve(scene.representation_uri)
    try:
        document = backend.build_camera_path(
            scene_uri,
            duration_sec=shot.duration_sec,
            fps=job.fps,
            width=job.width,
            height=job.height,
            easing=shot.easing,
        )
        proxy = backend.scene_proxy(scene_uri)
        meta = render_geometry_motion(
            scene_uri=str(scene_uri),
            camera_path=document,
            output=out_path,
            fps=job.fps,
            width=job.width,
            height=job.height,
            progress=progress,
            cancelled=cancelled,
            backend=backend,
            proxy=proxy,
        )
    except GeometryPathRejected as exc:
        return None, f"{messages.PATH_REJECTED} Reasons: {'; '.join(exc.reasons)}"
    except GeometryQualityRejected as exc:
        return None, f"{messages.SCENE_REJECTED} Reasons: {'; '.join(exc.reasons)}"
    except (GeometryUnavailable, GeometryError) as exc:
        return None, str(exc)

    meta["scene_id"] = scene.id
    meta["effective_mode"] = "geometry"
    return meta, None


def _process_timeline_render(db, job: RenderJob, progress, cancelled) -> None:
    """Render and concatenate all shots in the project into a continuous master MP4."""
    from app.models.entities import Project

    project = db.get(Project, job.project_id)
    if not project:
        job.status = "failed"; job.error = "Project not found"; db.commit(); return

    shots = list(db.scalars(select(Shot).where(Shot.project_id == job.project_id).order_by(Shot.created_at)))
    if not shots:
        job.status = "failed"; job.error = "No shots in project to assemble timeline"; db.commit(); return

    progress(0.1, f"Preparing timeline from {len(shots)} shots")
    shot_video_paths: list[Path] = []
    total_shots = len(shots)

    for i, shot in enumerate(shots):
        if cancelled():
            raise InterruptedError("cancel requested")

        # Check if an existing completed render job exists for this shot
        completed_job = db.scalars(
            select(RenderJob)
            .where(RenderJob.shot_id == shot.id, RenderJob.status == "completed", RenderJob.output_uri.isnot(None))
            .order_by(RenderJob.created_at.desc())
        ).first()

        if completed_job and completed_job.output_uri and storage.resolve(completed_job.output_uri).exists():
            shot_video_paths.append(storage.resolve(completed_job.output_uri))
        else:
            # Render this shot directly
            progress(0.1 + (0.7 * (i / total_shots)), f"Rendering shot {i + 1}/{total_shots}: {shot.name}")
            shot_assets = list(db.scalars(select(ImageAsset).where(ImageAsset.id.in_(shot.asset_ids))))
            by_id = {a.id: a for a in shot_assets}
            ordered = [by_id[aid] for aid in shot.asset_ids if aid in by_id]
            if not ordered:
                continue

            shot_out_rel = f"projects/{job.project_id}/renders/{shot.id}_auto.mp4"
            shot_out_path = settings_path(shot_out_rel)
            render_safe_motion(
                image_paths=[storage.resolve(a.storage_uri) for a in ordered],
                output=shot_out_path,
                duration_sec=shot.duration_sec,
                fps=job.fps,
                width=job.width,
                height=job.height,
                progress=lambda *_: None,
                cancelled=cancelled,
                overlay_title=shot.overlay_title,
                subtitle_text=shot.subtitle_text,
            )
            shot_video_paths.append(shot_out_path)

    if not shot_video_paths:
        job.status = "failed"; job.error = "Failed to render any valid shots for timeline"; db.commit(); return

    out_rel = f"projects/{job.project_id}/renders/timeline_{job.id}.mp4"
    out_path = settings_path(out_rel)
    bgm_path = storage.resolve(project.bgm_uri) if project.bgm_uri else None

    meta = concatenate_timeline(
        shot_video_paths=shot_video_paths,
        output=out_path,
        progress=progress,
        cancelled=cancelled,
        bgm_path=bgm_path,
    )

    if cancelled():
        job.status = "cancelled"; db.commit(); return

    job.output_uri = f"local://{out_rel}"
    job.provenance = {**(job.provenance or {}), **meta}
    job.progress = 1.0
    job.status = "completed"
    job.error = None
    db.commit()


def settings_path(rel: str) -> Path:
    # Use storage resolver without exposing arbitrary filesystem paths.
    return storage.resolve(f"local://{rel}")


def main():
    Base.metadata.create_all(engine)
    print("cinevideo render worker started", flush=True)
    while True:
        job_id = pop_render(timeout=2) or claim_fallback_job()
        if job_id:
            process(job_id)
        else:
            time.sleep(1)


if __name__ == "__main__":
    main()
