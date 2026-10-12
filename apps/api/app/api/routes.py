from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.entities import ImageAsset, Project, RenderJob, Scene, Shot
from app.schemas.contracts import (
    ApplyTemplateRequest,
    AssetOut,
    ProjectCreate,
    ProjectOut,
    RenderJobOut,
    RenderRequest,
    SceneCreate,
    SceneOut,
    ShotCreate,
    ShotOut,
    TimelineRenderRequest,
)
from app.services.ai_adapter import ai_adapter
from app.services.camera_modes import get_camera_modes_catalog, validate_camera_motion
from app.services.capabilities import get_capabilities
from app.services.image_analysis import analyze_image, select_mode
from app.services.infrastructure_templates import (
    generate_infrastructure_storyboard,
    get_infrastructure_templates,
    get_template_by_id,
)
from app.services.queue import enqueue_render
from app.services.scenes import select_scene_for_shot
from app.services.storage import storage

router = APIRouter(prefix="/api/v1")


def safe_name(name: str) -> str:
    name = Path(name or "image.jpg").name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:180]


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/capabilities")
def capabilities():
    return get_capabilities()


@router.get("/templates/infrastructure")
def list_infrastructure_templates():
    return get_infrastructure_templates()


@router.get("/camera-modes")
def list_camera_modes():
    return get_camera_modes_catalog()


@router.get("/ai-adapter/status")
def ai_adapter_status():
    return ai_adapter.is_available()


@router.post("/projects", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    item = Project(name=body.name)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    item = db.get(Project, project_id)
    if not item: raise HTTPException(404, "project not found")
    return item


@router.post("/projects/{project_id}/assets", response_model=AssetOut)
def upload_asset(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, "project not found")
    filename = safe_name(file.filename or "image.jpg")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(415, "supported formats: jpg, jpeg, png, webp")
    asset = ImageAsset(project_id=project_id, filename=filename, storage_uri="", sha256="")
    db.add(asset); db.flush()
    try:
        uri, digest = storage.save_stream(f"projects/{project_id}/originals/{asset.id}_{filename}", file.file)
    except Exception as e:
        db.rollback(); raise HTTPException(400, f"upload failed: {e}")
    asset.storage_uri = uri; asset.sha256 = digest
    db.commit(); db.refresh(asset)
    return asset


@router.get("/projects/{project_id}/assets", response_model=list[AssetOut])
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return list(db.scalars(select(ImageAsset).where(ImageAsset.project_id == project_id).order_by(ImageAsset.created_at)))


@router.post("/projects/{project_id}/analyze")
def analyze_project(project_id: str, db: Session = Depends(get_db)):
    assets = list(db.scalars(select(ImageAsset).where(ImageAsset.project_id == project_id)))
    if not assets: raise HTTPException(400, "upload at least one image")
    results = []
    for asset in assets:
        try:
            metrics = analyze_image(storage.resolve(asset.storage_uri))
            asset.width = metrics["width"]
            asset.height = metrics["height"]
            asset.sharpness_score = metrics["sharpness_score"]
            asset.exposure_score = metrics["exposure_score"]
            asset.analyzed = True
            results.append({"asset_id": asset.id, **metrics})
        except Exception as e:
            results.append({"asset_id": asset.id, "error": str(e)})
    caps = get_capabilities()
    mode = select_mode(len(assets), bool(caps["geometry"]["available"]))
    project = db.get(Project, project_id)
    if project: project.status = "analyzed"
    db.commit()
    return {"project_id": project_id, "suggested_mode": mode, "capabilities": caps, "assets": results}


# --------------------------------------------------------------------------- #
# Scenes (Phase 0 geometry spine: images -> reconstruction -> representation)
# --------------------------------------------------------------------------- #
@router.post("/projects/{project_id}/scenes", response_model=SceneOut)
def create_scene(project_id: str, body: SceneCreate, db: Session = Depends(get_db)):
    """Group images into a scene candidate; reconstruction is a separate job."""
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    assets = list(
        db.scalars(
            select(ImageAsset).where(
                ImageAsset.id.in_(body.asset_ids), ImageAsset.project_id == project_id
            )
        )
    )
    if len(assets) != len(set(body.asset_ids)):
        raise HTTPException(400, "one or more assets do not belong to project")
    caps = get_capabilities()
    mode = body.mode
    if mode == "auto":
        mode = select_mode(len(assets), bool(caps["geometry"]["available"]))
    scene = Scene(
        project_id=project_id,
        name=body.name,
        mode=mode,
        reconstruction_status="created",
        asset_ids=body.asset_ids,
        diagnostics={
            "asset_count": len(assets),
            "requested_mode": mode,
            "geometry_capability": caps["geometry"],
        },
    )
    db.add(scene); db.commit(); db.refresh(scene)
    return scene


@router.get("/projects/{project_id}/scenes", response_model=list[SceneOut])
def list_scenes(project_id: str, db: Session = Depends(get_db)):
    return list(db.scalars(select(Scene).where(Scene.project_id == project_id).order_by(Scene.created_at)))


@router.get("/scenes/{scene_id}", response_model=SceneOut)
def get_scene(scene_id: str, db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene: raise HTTPException(404, "scene not found")
    return scene


@router.post("/scenes/{scene_id}/reconstruct", response_model=RenderJobOut)
def reconstruct_scene(scene_id: str, db: Session = Depends(get_db)):
    """Queue COLMAP reconstruction. Never runs long work inside the request."""
    scene = db.get(Scene, scene_id)
    if not scene: raise HTTPException(404, "scene not found")
    caps = get_capabilities()
    if not caps["geometry"]["reconstruct_available"]:
        raise HTTPException(503, caps["geometry"]["reconstruct_reason"] or "COLMAP unavailable")
    job = RenderJob(
        project_id=scene.project_id,
        shot_id=None,
        type="reconstruction",
        status="queued",
        width=settings.render_preview_width,
        height=settings.render_preview_height,
        fps=settings.render_default_fps,
        mode="geometry",
        provenance={
            "engine_version": "0.1.0",
            "pipeline_schema_version": 1,
            "scene_id": scene.id,
            "asset_count": len(scene.asset_ids or []),
        },
    )
    db.add(job)
    scene.reconstruction_status = "queued"
    db.commit(); db.refresh(job)
    enqueue_render(job.id)
    return job


@router.post("/projects/{project_id}/shots", response_model=ShotOut)
def create_shot(project_id: str, body: ShotCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, "project not found")
    assets = list(db.scalars(select(ImageAsset).where(ImageAsset.id.in_(body.asset_ids), ImageAsset.project_id == project_id)))
    if len(assets) != len(set(body.asset_ids)):
        raise HTTPException(400, "one or more assets do not belong to project")
    mode = body.mode
    if mode == "auto":
        mode = select_mode(len(assets), get_capabilities()["geometry"]["available"])
    shot = Shot(
        project_id=project_id,
        name=body.name,
        template_id=body.template_id,
        asset_ids=body.asset_ids,
        duration_sec=min(body.duration_sec, settings.render_max_duration_sec),
        fps=body.fps,
        mode=mode,
        camera_mode=body.camera_mode,
        easing=body.easing,
        overlay_title=body.overlay_title,
        subtitle_text=body.subtitle_text,
        narration_text=body.narration_text,
        audio_uri=body.audio_uri,
        keyframes=[{"asset_id": aid, "index": i} for i, aid in enumerate(body.asset_ids)],
    )
    db.add(shot); db.commit(); db.refresh(shot)
    return shot


@router.post("/projects/{project_id}/apply-template", response_model=list[ShotOut])
def apply_infrastructure_template(
    project_id: str,
    body: ApplyTemplateRequest,
    db: Session = Depends(get_db),
):
    """Generate an infrastructure storyboard from the project's uploaded assets."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")

    assets = list(db.scalars(select(ImageAsset).where(ImageAsset.project_id == project_id).order_by(ImageAsset.created_at)))
    if not assets:
        raise HTTPException(400, "Vui lòng tải lên ít nhất một ảnh để tạo storyboard")

    asset_ids = [a.id for a in assets]
    storyboard = generate_infrastructure_storyboard(project.name, asset_ids)

    created_shots: list[Shot] = []
    for s in storyboard:
        shot = Shot(
            project_id=project_id,
            name=s["name"],
            template_id=s["template_id"],
            asset_ids=s["asset_ids"],
            duration_sec=s["duration_sec"],
            fps=s["fps"],
            mode="auto",
            camera_mode=s["camera_mode"],
            easing=s["easing"],
            overlay_title=s["overlay_title"],
            subtitle_text=s["subtitle_text"],
            narration_text=s["narration_text"],
            keyframes=[{"asset_id": aid, "index": i} for i, aid in enumerate(s["asset_ids"])],
        )
        db.add(shot)
        created_shots.append(shot)

    project.template_name = body.template_id or "infrastructure_8_shots"
    project.status = "storyboard_ready"
    db.commit()
    for s in created_shots:
        db.refresh(s)
    return created_shots


@router.post("/projects/{project_id}/render-timeline", response_model=RenderJobOut)
def render_project_timeline(
    project_id: str,
    body: TimelineRenderRequest,
    db: Session = Depends(get_db),
):
    """Queue a full project timeline assembly job."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")

    shots = list(db.scalars(select(Shot).where(Shot.project_id == project_id)))
    if not shots:
        raise HTTPException(400, "Dự án chưa có shot nào để xuất timeline")

    width = settings.render_final_width if body.resolution == "1080p" else 1280
    height = settings.render_final_height if body.resolution == "1080p" else 720

    job = RenderJob(
        project_id=project_id,
        shot_id=None,
        type="timeline",
        status="queued",
        width=width,
        height=height,
        fps=body.fps,
        mode="timeline_assembly",
        provenance={
            "engine_version": "0.1.0",
            "pipeline_schema_version": 1,
            "shot_count": len(shots),
            "include_subtitles": body.include_subtitles,
            "include_audio": body.include_audio,
        },
    )
    db.add(job); db.commit(); db.refresh(job)
    enqueue_render(job.id)
    return job


@router.get("/shots/{shot_id}", response_model=ShotOut)
def get_shot(shot_id: str, db: Session = Depends(get_db)):
    shot = db.get(Shot, shot_id)
    if not shot: raise HTTPException(404, "shot not found")
    return shot


def _new_job(db: Session, shot: Shot, kind: str, width: int, height: int, mode: str | None = None) -> RenderJob:
    scene = select_scene_for_shot(db, shot)
    provenance = {"engine_version": "0.1.0", "pipeline_schema_version": 1}
    if scene is not None:
        # The worker reuses this representation instead of reconstructing again.
        provenance["scene_id"] = scene.id
        provenance["scene_status"] = scene.reconstruction_status
        provenance["scene_uri"] = scene.representation_uri
    job = RenderJob(project_id=shot.project_id, shot_id=shot.id, type=kind, status="queued",
                    width=width, height=height, fps=shot.fps, mode=mode or shot.mode,
                    provenance=provenance)
    db.add(job); db.commit(); db.refresh(job)
    enqueue_render(job.id)
    return job


@router.post("/shots/{shot_id}/preview", response_model=RenderJobOut)
def preview(shot_id: str, db: Session = Depends(get_db)):
    shot = db.get(Shot, shot_id)
    if not shot: raise HTTPException(404, "shot not found")
    return _new_job(db, shot, "preview", settings.render_preview_width, settings.render_preview_height)


@router.post("/projects/{project_id}/render", response_model=RenderJobOut)
def render(project_id: str, body: RenderRequest, db: Session = Depends(get_db)):
    shot = db.get(Shot, body.shot_id)
    if not shot or shot.project_id != project_id: raise HTTPException(404, "shot not found")
    if body.resolution == "720p": width, height = 1280, 720
    elif body.resolution == "1080p": width, height = settings.render_final_width, settings.render_final_height
    else: raise HTTPException(400, "resolution must be 720p or 1080p in Core MVP")
    return _new_job(db, shot, "final", width, height, body.mode)


@router.get("/render-jobs/{job_id}", response_model=RenderJobOut)
def get_render_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(RenderJob, job_id)
    if not job: raise HTTPException(404, "render job not found")
    return job


@router.post("/render-jobs/{job_id}/cancel", response_model=RenderJobOut)
def cancel_render(job_id: str, db: Session = Depends(get_db)):
    job = db.get(RenderJob, job_id)
    if not job: raise HTTPException(404, "render job not found")
    job.cancel_requested = True
    if job.status == "queued": job.status = "cancelled"
    db.commit(); db.refresh(job)
    return job


@router.get("/render-jobs/{job_id}/download")
def download_render(job_id: str, db: Session = Depends(get_db)):
    job = db.get(RenderJob, job_id)
    if not job or job.status != "completed" or not job.output_uri:
        raise HTTPException(404, "completed output not found")
    path = storage.resolve(job.output_uri)
    return FileResponse(path, media_type="video/mp4", filename=f"{job.id}.mp4")
