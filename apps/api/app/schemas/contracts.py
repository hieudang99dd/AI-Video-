from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectOut(BaseModel):
    id: str
    name: str
    status: str
    template_name: str | None = None
    bgm_uri: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class AssetOut(BaseModel):
    id: str
    project_id: str
    filename: str
    width: int | None
    height: int | None
    sharpness_score: float | None
    exposure_score: float | None
    analyzed: bool
    model_config = {"from_attributes": True}


class ShotCreate(BaseModel):
    name: str = "Shot 01"
    asset_ids: list[str] = Field(min_length=1)
    duration_sec: float = Field(default=5.0, gt=0, le=30)
    fps: int = Field(default=30, ge=12, le=60)
    mode: str = "auto"
    camera_mode: str = "2D_IMAGE_CAMERA"
    template_id: str | None = None
    easing: str = "cinematic"
    overlay_title: str | None = None
    subtitle_text: str | None = None
    narration_text: str | None = None
    audio_uri: str | None = None


class ShotOut(BaseModel):
    id: str
    project_id: str
    name: str
    template_id: str | None = None
    asset_ids: list[str]
    duration_sec: float
    fps: int
    mode: str
    camera_mode: str = "2D_IMAGE_CAMERA"
    easing: str
    overlay_title: str | None = None
    subtitle_text: str | None = None
    narration_text: str | None = None
    audio_uri: str | None = None
    model_config = {"from_attributes": True}


class ApplyTemplateRequest(BaseModel):
    template_id: str | None = None


class TimelineRenderRequest(BaseModel):
    resolution: str = "1080p"
    fps: int = 30
    include_subtitles: bool = True
    include_audio: bool = True


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
    representation_uri: str | None
    asset_ids: list[str]
    diagnostics: dict
    model_config = {"from_attributes": True}


class RenderJobOut(BaseModel):
    id: str
    project_id: str
    shot_id: str | None
    type: str
    status: str
    progress: float
    width: int
    height: int
    fps: int
    mode: str
    output_uri: str | None
    error: str | None
    provenance: dict
    model_config = {"from_attributes": True}
