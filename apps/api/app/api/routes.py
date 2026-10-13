from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.entities import AIJob, ImageAsset, Project, RenderJob, Scene, Shot
from app.schemas.contracts import (
    AIEnhanceRequest,
    AIJobOut,
    AIQCDecisionRequest,
    ApplyTemplateRequest,
    AssetOrderRequest,
    AssetOut,
    AssetUpdateRequest,
    BlenderExportRequest,
    CameraPresetCreateRequest,
    GenerateCameraPathRequest,
    ProjectCreate,
    ProjectOut,
    RenderJobOut,
    RenderRequest,
    SceneCreate,
    SceneOut,
    ShotCreate,
    ShotOut,
    TimelineRenderRequest,
    UpdateCameraPathRequest,
)
from app.services.ai_adapter import ai_adapter, get_all_ai_modules_status, wan22_adapter
from app.services.ai_qc import AI_ENHANCED_DISCLAIMER, evaluate_ai_enhancement_qc
from app.services.blender_engine import export_and_optionally_run_blender_scene
from app.services.camera_modes import get_camera_modes_catalog, validate_camera_motion
from app.services.camera_planner import (
    CATEGORY_TO_DEFAULT_PRESET,
    generate_shot_camera_plan,
    get_all_camera_presets,
    save_custom_preset,
)
from app.services.capabilities import get_capabilities
from app.services.image_analysis import (
    SEMANTIC_CATEGORIES,
    analyze_image,
    build_project_manifest,
    detect_duplicates_and_overlaps,
    select_mode,
)
from app.services.infrastructure_templates import (
    generate_infrastructure_storyboard,
    get_infrastructure_templates,
    get_template_by_id,
)
from app.services.job_manager import PipelineState, validate_upload_safety
from app.services.queue import enqueue_render
from app.services.scenes import select_scene_for_shot, storage_uri_for
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


@router.get("/camera-presets")
def list_camera_presets():
    return get_all_camera_presets()


@router.post("/camera-presets/custom")
def create_custom_camera_preset(body: CameraPresetCreateRequest):
    return save_custom_preset(body.model_dump())


@router.get("/ai-adapter/status")
def ai_adapter_status():
    return ai_adapter.is_available()


@router.get("/ai-modules/status")
def ai_modules_status():
    return get_all_ai_modules_status()


@router.post("/projects", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    item = Project(
        name=body.name,
        source_type=body.source_type,
        settings_json=body.settings_json,
        pipeline_state=PipelineState.CREATED.value,
    )
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
    existing_count = len(list(db.scalars(select(ImageAsset).where(ImageAsset.project_id == project_id))))
    filename = safe_name(file.filename or "image.jpg")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(415, "supported formats: jpg, jpeg, png, webp")
    try:
        validate_upload_safety(filename, current_project_assets=existing_count)
    except ValueError as e:
        raise HTTPException(400, str(e))
    asset = ImageAsset(
        project_id=project_id,
        filename=filename,
        storage_uri="",
        sha256="",
        sequence_index=existing_count,
    )
    db.add(asset); db.flush()
    try:
        uri, digest = storage.save_stream(
            f"projects/{project_id}/originals/{asset.id}_{filename}",
            file.file,
            max_bytes=int(settings.max_upload_size_mb * 1024 * 1024),
            verify_image=True,
        )
    except ValueError as exc:
        db.rollback()
        code = str(exc)
        status_code = 413 if code in {"UPLOAD_TOO_LARGE", "IMAGE_PIXEL_LIMIT_EXCEEDED"} else 422
        raise HTTPException(status_code, code) from None
    except Exception:
        db.rollback()
        raise HTTPException(400, "Upload failed validation or storage. No asset was saved.") from None
    resolved = storage.resolve(uri)
    asset.storage_uri = uri
    asset.sha256 = digest
    asset.file_size_bytes = resolved.stat().st_size if resolved.exists() else None
    db.commit(); db.refresh(asset)
    return asset


@router.get("/projects/{project_id}/assets", response_model=list[AssetOut])
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(ImageAsset)
            .where(ImageAsset.project_id == project_id)
            .order_by(ImageAsset.sequence_index, ImageAsset.created_at)
        )
    )


@router.patch("/projects/{project_id}/assets/{asset_id}", response_model=AssetOut)
def update_asset_metadata(
    project_id: str,
    asset_id: str,
    body: AssetUpdateRequest,
    db: Session = Depends(get_db),
):
    asset = db.get(ImageAsset, asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(404, "asset not found")
    if body.sequence_index is not None:
        asset.sequence_index = body.sequence_index
    if body.scene_group is not None:
        asset.scene_group = body.scene_group
    if body.semantic_category is not None:
        if body.semantic_category not in SEMANTIC_CATEGORIES:
            raise HTTPException(400, f"semantic_category must be one of {SEMANTIC_CATEGORIES}")
        asset.semantic_category = body.semantic_category
        asset.user_overridden_category = True
        asset.semantic_confidence = 1.0
    if body.metadata_json is not None:
        asset.metadata_json = {**(asset.metadata_json or {}), **body.metadata_json}
    db.commit(); db.refresh(asset)
    return asset


@router.put("/projects/{project_id}/assets/order", response_model=list[AssetOut])
def reorder_project_assets(
    project_id: str,
    body: AssetOrderRequest,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")
    assets = list(db.scalars(select(ImageAsset).where(ImageAsset.project_id == project_id)))
    by_id = {a.id: a for a in assets}
    for idx, aid in enumerate(body.ordered_asset_ids):
        if aid in by_id:
            by_id[aid].sequence_index = idx
            if body.scene_group:
                by_id[aid].scene_group = body.scene_group
    db.commit()
    return list(
        db.scalars(
            select(ImageAsset)
            .where(ImageAsset.project_id == project_id)
            .order_by(ImageAsset.sequence_index, ImageAsset.created_at)
        )
    )


@router.post("/projects/{project_id}/analyze")
def analyze_project(project_id: str, db: Session = Depends(get_db)):
    assets = list(
        db.scalars(
            select(ImageAsset)
            .where(ImageAsset.project_id == project_id)
            .order_by(ImageAsset.sequence_index, ImageAsset.created_at)
        )
    )
    if not assets: raise HTTPException(400, "upload at least one image")
    results = []
    dup_inputs = []
    for idx, asset in enumerate(assets):
        try:
            img_path = storage.resolve(asset.storage_uri)
            metrics = analyze_image(img_path)
            asset.width = metrics["width"]
            asset.height = metrics["height"]
            asset.file_size_bytes = metrics["file_size_bytes"]
            asset.aspect_ratio = metrics["aspect_ratio"]
            asset.sharpness_score = metrics["sharpness_score"]
            asset.exposure_score = metrics["exposure_score"]
            asset.perceptual_hash = metrics["perceptual_hash"]
            if not asset.user_overridden_category:
                asset.semantic_category = metrics["semantic_category"]
                asset.semantic_confidence = metrics["semantic_confidence"]
            asset.quality_warnings = metrics["quality_warnings"]
            asset.metadata_json = {**(asset.metadata_json or {}), "exif": metrics.get("exif", {})}
            asset.analyzed = True
            dup_inputs.append(
                {
                    "id": asset.id,
                    "sha256": asset.sha256,
                    "perceptual_hash": asset.perceptual_hash,
                    "path": img_path,
                    "quality_warnings": asset.quality_warnings,
                    "metrics": metrics,
                }
            )
        except Exception as e:
            results.append({"asset_id": asset.id, "error": str(e)})

    if dup_inputs:
        annotated = detect_duplicates_and_overlaps(dup_inputs)
        by_id = {a.id: a for a in assets}
        for rec in annotated:
            a_obj = by_id[rec["id"]]
            a_obj.is_duplicate = rec["is_duplicate"]
            a_obj.duplicate_of = rec["duplicate_of"]
            a_obj.overlap_score = rec["overlap_score"]
            a_obj.quality_warnings = rec["quality_warnings"]
            results.append(
                {
                    "asset_id": a_obj.id,
                    **rec["metrics"],
                    "semantic_category": a_obj.semantic_category,
                    "is_duplicate": a_obj.is_duplicate,
                    "duplicate_of": a_obj.duplicate_of,
                    "overlap_score": a_obj.overlap_score,
                    "quality_warnings": a_obj.quality_warnings,
                }
            )

    caps = get_capabilities()
    mode = select_mode(len(assets), bool(caps["geometry"]["available"]))
    project = db.get(Project, project_id)
    if project:
        project.status = "analyzed"
        project.pipeline_state = PipelineState.VALIDATING.value
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
        scale_status="uncalibrated",
        coordinate_system="uncalibrated_local",
        unit="relative_units",
        anchor_point=[0.0, 0.0, 0.0],
        allowed_camera_bounds={"min_x": -50.0, "max_x": 50.0, "min_y": -50.0, "max_y": 50.0, "min_z": 0.5, "max_z": 40.0},
        asset_ids=body.asset_ids,
        diagnostics={
            "asset_count": len(assets),
            "requested_mode": mode,
            "geometry_capability": caps["geometry"],
            "scale_status": "uncalibrated",
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
        state_machine_step=PipelineState.RECONSTRUCTING.value,
        width=settings.render_preview_width,
        height=settings.render_preview_height,
        fps=settings.render_default_fps,
        mode="geometry",
        provenance={
            "engine_version": "0.2.0",
            "pipeline_schema_version": 2,
            "scene_id": scene.id,
            "asset_count": len(scene.asset_ids or []),
            "scale_status": "uncalibrated",
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

    plan = generate_shot_camera_plan(
        preset_id=body.preset,
        source_mode=body.source_mode,
        asset_ids=body.asset_ids,
        duration_sec=min(body.duration_sec, settings.render_max_duration_sec),
        fps=body.fps,
        fov_deg=body.fov_deg,
        speed=body.speed,
        shake_level=body.shake_level,
        easing=body.easing,
    )
    shot = Shot(
        project_id=project_id,
        scene_id=body.scene_id,
        name=body.name,
        template_id=body.template_id,
        preset=body.preset,
        source_mode=plan["source_mode"],
        asset_ids=body.asset_ids,
        duration_sec=min(body.duration_sec, settings.render_max_duration_sec),
        fps=body.fps,
        fov_deg=body.fov_deg,
        speed=body.speed,
        shake_level=body.shake_level,
        transition_rule=body.transition_rule,
        confidence=plan["confidence"],
        mode=mode,
        camera_mode=body.camera_mode,
        easing=body.easing,
        overlay_title=body.overlay_title,
        subtitle_text=body.subtitle_text,
        narration_text=body.narration_text,
        audio_uri=body.audio_uri,
        keyframes=[{"asset_id": aid, "index": i} for i, aid in enumerate(body.asset_ids)],
        start_pose=plan["start_pose"],
        end_pose=plan["end_pose"],
        trajectory=plan["trajectory"],
        ai_enabled=body.ai_enabled,
        ai_status="ready" if body.ai_enabled else "disabled",
    )
    db.add(shot); db.commit(); db.refresh(shot)
    return shot


@router.get("/projects/{project_id}/shots", response_model=list[ShotOut])
def list_project_shots(project_id: str, db: Session = Depends(get_db)):
    return list(db.scalars(select(Shot).where(Shot.project_id == project_id).order_by(Shot.created_at)))


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

    assets = list(
        db.scalars(
            select(ImageAsset)
            .where(ImageAsset.project_id == project_id)
            .order_by(ImageAsset.sequence_index, ImageAsset.created_at)
        )
    )
    if not assets:
        raise HTTPException(400, "Vui lòng tải lên ít nhất một ảnh để tạo storyboard")

    asset_ids = [a.id for a in assets]
    storyboard = generate_infrastructure_storyboard(project.name, asset_ids)
    preset_mapping = {
        "project_overview": "establishing_shot",
        "alignment_plan": "aerial_flyover",
        "profile_view": "follow_road",
        "cross_sections": "approach_shot",
        "bridges_interchanges": "orbit_shot",
        "drainage_system": "culvert_drainage_detail",
        "traffic_safety": "low_angle_road",
        "project_outro": "closing_shot",
    }

    created_shots: list[Shot] = []
    for s in storyboard:
        preset_id = preset_mapping.get(s["template_id"], "establishing_shot")
        plan = generate_shot_camera_plan(
            preset_id=preset_id,
            source_mode="auto",
            asset_ids=s["asset_ids"],
            duration_sec=s["duration_sec"],
            fps=s["fps"],
            easing=s["easing"],
        )
        shot = Shot(
            project_id=project_id,
            name=s["name"],
            template_id=s["template_id"],
            preset=preset_id,
            source_mode=plan["source_mode"],
            asset_ids=s["asset_ids"],
            duration_sec=s["duration_sec"],
            fps=s["fps"],
            fov_deg=plan["fov_deg"],
            speed=plan["speed"],
            shake_level=plan["shake_level"],
            transition_rule=plan["transition_rule"],
            confidence=plan["confidence"],
            mode="auto",
            camera_mode=s["camera_mode"],
            easing=s["easing"],
            overlay_title=s["overlay_title"],
            subtitle_text=s["subtitle_text"],
            narration_text=s["narration_text"],
            keyframes=[{"asset_id": aid, "index": i} for i, aid in enumerate(s["asset_ids"])],
            start_pose=plan["start_pose"],
            end_pose=plan["end_pose"],
            trajectory=plan["trajectory"],
        )
        db.add(shot)
        created_shots.append(shot)

    project.template_name = body.template_id or "infrastructure_8_shots"
    project.status = "storyboard_ready"
    project.pipeline_state = PipelineState.CAMERA_PLANNING.value
    db.commit()
    for s in created_shots:
        db.refresh(s)
    return created_shots


@router.post("/shots/{shot_id}/camera-path/generate", response_model=ShotOut)
def generate_shot_camera_trajectory(
    shot_id: str,
    body: GenerateCameraPathRequest,
    db: Session = Depends(get_db),
):
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(404, "shot not found")
    scene = select_scene_for_shot(db, shot)
    scene_poses = list(scene.camera_poses or []) if scene and scene.reconstruction_status == "ready" else None
    scene_anchor = list(scene.anchor_point or [0.0, 0.0, 0.0]) if scene else [0.0, 0.0, 0.0]
    scene_bounds = dict(scene.allowed_camera_bounds or {}) if scene else {}

    plan = generate_shot_camera_plan(
        preset_id=body.preset,
        source_mode=body.source_mode,
        asset_ids=shot.asset_ids,
        duration_sec=body.duration_sec or shot.duration_sec,
        fps=body.fps or shot.fps,
        fov_deg=body.fov_deg,
        speed=body.speed,
        shake_level=body.shake_level,
        easing=body.easing or shot.easing,
        scene_anchor=scene_anchor,
        scene_bounds=scene_bounds,
        reconstructed_poses=scene_poses,
        use_moverse=body.use_moverse,
    )
    shot.preset = plan["preset"]
    shot.source_mode = plan["source_mode"]
    shot.duration_sec = plan["duration_sec"]
    shot.fps = plan["fps"]
    shot.fov_deg = plan["fov_deg"]
    shot.speed = plan["speed"]
    shot.shake_level = plan["shake_level"]
    shot.easing = plan["easing"]
    shot.transition_rule = plan["transition_rule"]
    shot.confidence = plan["confidence"]
    shot.start_pose = plan["start_pose"]
    shot.end_pose = plan["end_pose"]
    shot.trajectory = plan["trajectory"]
    db.commit(); db.refresh(shot)
    return shot


@router.put("/shots/{shot_id}/camera-path", response_model=ShotOut)
def update_shot_camera_trajectory(
    shot_id: str,
    body: UpdateCameraPathRequest,
    db: Session = Depends(get_db),
):
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(404, "shot not found")
    for field_name in (
        "preset",
        "source_mode",
        "duration_sec",
        "fps",
        "fov_deg",
        "speed",
        "shake_level",
        "easing",
        "transition_rule",
        "start_pose",
        "end_pose",
        "trajectory",
        "overlay_title",
        "subtitle_text",
        "narration_text",
    ):
        val = getattr(body, field_name)
        if val is not None:
            setattr(shot, field_name, val)
    db.commit(); db.refresh(shot)
    return shot


@router.post("/shots/{shot_id}/blender-scene")
def export_blender_scene_for_shot(
    shot_id: str,
    body: BlenderExportRequest,
    db: Session = Depends(get_db),
):
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(404, "shot not found")
    assets = list(db.scalars(select(ImageAsset).where(ImageAsset.id.in_(shot.asset_ids))))
    by_id = {a.id: a for a in assets}
    ordered = [by_id[aid] for aid in shot.asset_ids if aid in by_id]
    image_paths = [storage.resolve(a.storage_uri) for a in ordered]

    width, height = (1920, 1080) if body.resolution == "1080p" else (1280, 720)
    camera_plan = {
        "preset": shot.preset,
        "source_mode": shot.source_mode,
        "duration_sec": shot.duration_sec,
        "fps": shot.fps,
        "fov_deg": shot.fov_deg,
        "start_pose": shot.start_pose,
        "end_pose": shot.end_pose,
        "trajectory": shot.trajectory,
    }
    blender_dir = storage.resolve(f"local://projects/{shot.project_id}/blender")
    output_mp4 = storage.resolve(f"local://projects/{shot.project_id}/renders/blender_{shot.id}.mp4")

    result = export_and_optionally_run_blender_scene(
        shot_id=shot.id,
        shot_name=shot.name,
        camera_plan=camera_plan,
        image_paths=image_paths,
        workdir=blender_dir,
        output_mp4_path=output_mp4,
        width=width,
        height=height,
        fps=shot.fps,
        execute_if_available=body.execute_if_available,
    )
    shot.blender_script_uri = storage_uri_for(Path(result["blender_script_path"]))
    shot.camera_path_uri = storage_uri_for(Path(result["camera_trajectory_path"]))
    db.commit()
    return result


@router.post("/shots/{shot_id}/ai-enhance", response_model=AIJobOut)
def run_shot_ai_enhancement(
    shot_id: str,
    body: AIEnhanceRequest,
    db: Session = Depends(get_db),
):
    """Run optional AI enhancement + automatic structural QC comparison."""
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(404, "shot not found")

    # P01: NEVER report an AI job as completed without verified inference.
    # The adapter is deliberately unavailable until Phase 09 supplies an
    # out-of-process runner with artifacts and comparable video frame QC.
    if body.module_name != "wan2_2":
        raise HTTPException(422, "Unsupported AI module; no video has been generated.")

    completed_render = db.scalars(
        select(RenderJob)
        .where(RenderJob.shot_id == shot.id, RenderJob.status == "completed", RenderJob.output_uri.isnot(None))
        .order_by(RenderJob.created_at.desc())
    ).first()
    if not completed_render or not completed_render.output_uri or not storage.resolve(completed_render.output_uri).is_file():
        raise HTTPException(422, "Render a source clip first. AI job was not created.")

    raise HTTPException(
        status_code=503,
        detail="Wan2.2 inference is not implemented. No AI job was started and no QC result exists.",
    )

@router.post("/shots/{shot_id}/ai-qc/decision", response_model=ShotOut)
def decide_shot_ai_qc(
    shot_id: str,
    body: AIQCDecisionRequest,
    db: Session = Depends(get_db),
):
    """Accept, reject (revert to original 3D/plate render), or selectively approve AI output."""
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(404, "shot not found")

    latest_ai_job = db.scalars(
        select(AIJob).where(AIJob.shot_id == shot_id).order_by(AIJob.created_at.desc())
    ).first()
    if body.decision != "rejected":
        if (
            latest_ai_job is None
            or latest_ai_job.status != "completed"
            or not latest_ai_job.qc_passed
            or not latest_ai_job.ai_output_uri
            or not storage.resolve(latest_ai_job.ai_output_uri).is_file()
        ):
            raise HTTPException(409, "No independently QC-passed AI video exists to approve.")
    if latest_ai_job:
        latest_ai_job.user_decision = body.decision

    if body.decision == "rejected":
        shot.ai_enabled = False
        shot.ai_status = "rejected_reverted_to_3d"
    elif body.decision == "accepted":
        shot.ai_enabled = True
        shot.ai_status = "accepted"
    else:
        shot.ai_enabled = True
        shot.ai_status = "selective"

    shot.qc_report = {
        **(shot.qc_report or {}),
        "user_decision": body.decision,
        "decision_notes": body.notes,
        "disclaimer": AI_ENHANCED_DISCLAIMER if shot.ai_enabled else "Original 3D/Plate Render (No AI modification)",
    }
    db.commit(); db.refresh(shot)
    return shot


@router.get("/projects/{project_id}/manifest")
def get_project_manifest(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")
    assets = list(
        db.scalars(
            select(ImageAsset)
            .where(ImageAsset.project_id == project_id)
            .order_by(ImageAsset.sequence_index, ImageAsset.created_at)
        )
    )
    scenes = list(db.scalars(select(Scene).where(Scene.project_id == project_id).order_by(Scene.created_at)))
    shots = list(db.scalars(select(Shot).where(Shot.project_id == project_id).order_by(Shot.created_at)))
    render_jobs = list(db.scalars(select(RenderJob).where(RenderJob.project_id == project_id).order_by(RenderJob.created_at)))
    ai_jobs = list(db.scalars(select(AIJob).where(AIJob.project_id == project_id).order_by(AIJob.created_at)))

    manifest = build_project_manifest(project, assets, scenes, shots, render_jobs, ai_jobs)
    manifest_rel = f"projects/{project_id}/manifest.json"
    manifest_path = storage.resolve(f"local://{manifest_rel}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    project.manifest_uri = f"local://{manifest_rel}"
    db.commit()
    return manifest


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
        state_machine_step=PipelineState.CREATED.value,
        width=width,
        height=height,
        fps=body.fps,
        mode="timeline_assembly",
        provenance={
            "engine_version": "0.2.0",
            "pipeline_schema_version": 2,
            "shot_count": len(shots),
            "include_subtitles": body.include_subtitles,
            "include_audio": body.include_audio,
            "intro_title": body.intro_title,
            "outro_title": body.outro_title,
            "project_info_overlay": body.project_info_overlay,
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
    provenance = {
        "engine_version": "0.2.0",
        "pipeline_schema_version": 2,
        "camera_source_mode": getattr(shot, "source_mode", "C_SINGLE_IMAGE_2_5D"),
        "camera_preset": getattr(shot, "preset", "establishing_shot"),
    }
    if scene is not None:
        # The worker reuses this representation instead of reconstructing again.
        provenance["scene_id"] = scene.id
        provenance["scene_status"] = scene.reconstruction_status
        provenance["scene_uri"] = scene.representation_uri
        provenance["scale_status"] = scene.scale_status
    job = RenderJob(
        project_id=shot.project_id,
        shot_id=shot.id,
        type=kind,
        status="queued",
        state_machine_step=PipelineState.CREATED.value,
        width=width,
        height=height,
        fps=shot.fps,
        mode=mode or shot.mode,
        provenance=provenance,
    )
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


@router.post("/render-jobs/{job_id}/run-now", response_model=RenderJobOut)
def run_render_job_now(job_id: str, db: Session = Depends(get_db)):
    """Execute a queued render job immediately in-process (for local studio workflow without Redis)."""
    job = db.get(RenderJob, job_id)
    if not job:
        raise HTTPException(404, "render job not found")
    if job.status in {"queued", "retry_wait"}:
        from app.workers.render_worker import process

        process(job_id)
        db.expire_all()
        job = db.get(RenderJob, job_id)
    return job


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
    if job.status == "queued":
        job.status = "cancelled"
        job.state_machine_step = PipelineState.CANCELLED.value
    db.commit(); db.refresh(job)
    return job


@router.get("/render-jobs/{job_id}/download")
def download_render(job_id: str, db: Session = Depends(get_db)):
    job = db.get(RenderJob, job_id)
    if not job or job.status != "completed" or not job.output_uri:
        raise HTTPException(404, "completed output not found")
    path = storage.resolve(job.output_uri)
    return FileResponse(path, media_type="video/mp4", filename=f"{job.id}.mp4")

