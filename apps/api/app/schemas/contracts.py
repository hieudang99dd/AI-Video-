from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str = "civil3d_infraworks"
    settings_json: dict[str, Any] = Field(default_factory=dict)


class ProjectOut(BaseModel):
    id: str
    name: str
    status: str
    source_type: str = "civil3d_infraworks"
    pipeline_state: str = "CREATED"
    template_name: str | None = None
    bgm_uri: str | None = None
    manifest_uri: str | None = None
    settings_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    model_config = {"from_attributes": True}


class AssetOut(BaseModel):
    id: str
    project_id: str
    filename: str
    file_size_bytes: int | None = None
    width: int | None
    height: int | None
    aspect_ratio: float | None = None
    sharpness_score: float | None
    exposure_score: float | None
    sequence_index: int = 0
    scene_group: str = "default"
    semantic_category: str = "road"
    semantic_confidence: float = 0.5
    user_overridden_category: bool = False
    perceptual_hash: str | None = None
    is_duplicate: bool = False
    duplicate_of: str | None = None
    overlap_score: float | None = None
    quality_warnings: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    analyzed: bool
    model_config = {"from_attributes": True}


class AssetUpdateRequest(BaseModel):
    sequence_index: int | None = None
    scene_group: str | None = None
    semantic_category: str | None = None
    metadata_json: dict[str, Any] | None = None


class AssetOrderRequest(BaseModel):
    ordered_asset_ids: list[str] = Field(min_length=1)
    scene_group: str | None = None


class ShotCreate(BaseModel):
    name: str = "Shot 01"
    asset_ids: list[str] = Field(min_length=1)
    scene_id: str | None = None
    duration_sec: float = Field(default=5.0, gt=0, le=30)
    fps: int = Field(default=30, ge=12, le=60)
    mode: str = "auto"
    camera_mode: str = "2D_IMAGE_CAMERA"
    preset: str = "establishing_shot"
    source_mode: str = "C_SINGLE_IMAGE_2_5D"
    fov_deg: float = Field(default=50.0, ge=15.0, le=120.0)
    speed: float = Field(default=1.0, gt=0.1, le=3.0)
    shake_level: float = Field(default=0.0, ge=0.0, le=1.0)
    transition_rule: str = "crossfade"
    template_id: str | None = None
    easing: str = "cinematic"
    overlay_title: str | None = None
    subtitle_text: str | None = None
    narration_text: str | None = None
    audio_uri: str | None = None
    ai_enabled: bool = False


class ShotOut(BaseModel):
    id: str
    project_id: str
    scene_id: str | None = None
    name: str
    template_id: str | None = None
    preset: str = "establishing_shot"
    source_mode: str = "C_SINGLE_IMAGE_2_5D"
    asset_ids: list[str]
    duration_sec: float
    fps: int
    fov_deg: float = 50.0
    speed: float = 1.0
    shake_level: float = 0.0
    mode: str
    camera_mode: str = "2D_IMAGE_CAMERA"
    easing: str
    transition_rule: str = "crossfade"
    confidence: float = 1.0
    overlay_title: str | None = None
    subtitle_text: str | None = None
    narration_text: str | None = None
    audio_uri: str | None = None
    start_pose: dict[str, Any] = Field(default_factory=dict)
    end_pose: dict[str, Any] = Field(default_factory=dict)
    trajectory: list[dict[str, Any]] = Field(default_factory=list)
    blender_script_uri: str | None = None
    camera_path_uri: str | None = None
    ai_enabled: bool = False
    ai_status: str = "disabled"
    ai_output_uri: str | None = None
    qc_report: dict[str, Any] = Field(default_factory=dict)
    model_config = {"from_attributes": True}


class ApplyTemplateRequest(BaseModel):
    template_id: str | None = None


class TimelineRenderRequest(BaseModel):
    resolution: str = "1080p"
    fps: int = 30
    include_subtitles: bool = True
    include_audio: bool = True
    intro_title: str | None = None
    outro_title: str | None = None
    project_info_overlay: str | None = None


class RenderRequest(BaseModel):
    shot_id: str
    resolution: str = "1080p"
    mode: str | None = None


class SceneCreate(BaseModel):
    name: str = "Scene 01"
    asset_ids: list[str] = Field(min_length=1)
    mode: str = "auto"


class SceneOut(BaseModel):
    id: str
    project_id: str
    name: str
    mode: str
    reconstruction_status: str
    confidence: float
    scale_status: str = "uncalibrated"
    coordinate_system: str = "uncalibrated_local"
    unit: str = "relative_units"
    representation_uri: str | None
    point_cloud_uri: str | None = None
    mesh_uri: str | None = None
    anchor_point: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    allowed_camera_bounds: dict[str, Any] = Field(default_factory=dict)
    camera_poses: list[dict[str, Any]] = Field(default_factory=list)
    asset_ids: list[str]
    diagnostics: dict
    model_config = {"from_attributes": True}


class RenderJobOut(BaseModel):
    id: str
    project_id: str
    shot_id: str | None
    type: str
    status: str
    state_machine_step: str = "CREATED"
    progress: float
    width: int
    height: int
    fps: int
    mode: str
    output_uri: str | None
    error: str | None
    provenance: dict
    model_config = {"from_attributes": True}


class CameraPresetCreateRequest(BaseModel):
    id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    base_preset_id: str = "establishing_shot"
    fov_deg: float = 50.0
    duration_sec: float = 6.0
    speed: float = 1.0
    shake_level: float = 0.0
    easing: str = "cinematic"
    start_offset: list[float] = Field(default_factory=lambda: [0.0, -5.0, 2.5])
    end_offset: list[float] = Field(default_factory=lambda: [0.0, -2.0, 1.8])
    look_at_offset: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])


class GenerateCameraPathRequest(BaseModel):
    preset: str = "establishing_shot"
    source_mode: str = "auto"
    duration_sec: float | None = None
    fps: int | None = None
    fov_deg: float | None = None
    speed: float | None = None
    shake_level: float | None = None
    easing: str | None = None
    use_moverse: bool = False


class UpdateCameraPathRequest(BaseModel):
    preset: str | None = None
    source_mode: str | None = None
    duration_sec: float | None = None
    fps: int | None = None
    fov_deg: float | None = None
    speed: float | None = None
    shake_level: float | None = None
    easing: str | None = None
    transition_rule: str | None = None
    start_pose: dict[str, Any] | None = None
    end_pose: dict[str, Any] | None = None
    trajectory: list[dict[str, Any]] | None = None
    overlay_title: str | None = None
    subtitle_text: str | None = None
    narration_text: str | None = None


class BlenderExportRequest(BaseModel):
    execute_if_available: bool = True
    resolution: str = "720p"


class AIEnhanceRequest(BaseModel):
    module_name: str = "wan2_2"
    prompt: str = "High-detail infrastructure engineering visualization, realistic asphalt, concrete bridge piers, natural daylight, stable geometry"
    seed: int = 42


class AIQCDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(accepted|rejected|selective)$")
    notes: str | None = None


class AIJobOut(BaseModel):
    id: str
    project_id: str
    shot_id: str | None
    module_name: str
    model_id: str
    status: str
    prompt: str
    seed: int
    source_render_uri: str | None
    ai_output_uri: str | None
    qc_passed: bool
    user_decision: str
    qc_metrics: dict[str, Any]
    disclaimer: str
    error: str | None
    created_at: datetime
    model_config = {"from_attributes": True}

