from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="created")
    source_type: Mapped[str] = mapped_column(String(64), default="civil3d_infraworks")
    pipeline_state: Mapped[str] = mapped_column(String(40), default="CREATED")
    template_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bgm_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    assets: Mapped[list["ImageAsset"]] = relationship(cascade="all, delete-orphan")
    shots: Mapped[list["Shot"]] = relationship(cascade="all, delete-orphan")


class ImageAsset(Base):
    __tablename__ = "image_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_uri: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    exposure_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sequence_index: Mapped[int] = mapped_column(Integer, default=0)
    scene_group: Mapped[str] = mapped_column(String(100), default="default")
    semantic_category: Mapped[str] = mapped_column(String(64), default="road")
    semantic_confidence: Mapped[float] = mapped_column(Float, default=0.5)
    user_overridden_category: Mapped[bool] = mapped_column(Boolean, default=False)
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    overlap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Shot(Base):
    __tablename__ = "shots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(200), default="Shot")
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preset: Mapped[str] = mapped_column(String(64), default="establishing_shot")
    source_mode: Mapped[str] = mapped_column(String(64), default="C_SINGLE_IMAGE_2_5D")
    mode: Mapped[str] = mapped_column(String(32), default="auto")
    camera_mode: Mapped[str] = mapped_column(String(32), default="2D_IMAGE_CAMERA")
    duration_sec: Mapped[float] = mapped_column(Float, default=5.0)
    fps: Mapped[int] = mapped_column(Integer, default=30)
    fov_deg: Mapped[float] = mapped_column(Float, default=50.0)
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    shake_level: Mapped[float] = mapped_column(Float, default=0.0)
    easing: Mapped[str] = mapped_column(String(32), default="cinematic")
    transition_rule: Mapped[str] = mapped_column(String(32), default="crossfade")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    overlay_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    keyframes: Mapped[list[dict]] = mapped_column(JSON, default=list)
    start_pose: Mapped[dict] = mapped_column(JSON, default=dict)
    end_pose: Mapped[dict] = mapped_column(JSON, default=dict)
    trajectory: Mapped[list[dict]] = mapped_column(JSON, default=list)
    blender_script_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_path_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_status: Mapped[str] = mapped_column(String(40), default="disabled")
    ai_output_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    qc_report: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Scene(Base):
    """A group of images that share verified geometry (Phase 0 geometry spine).

    ``representation_uri`` points at the persistent sparse model / 3DGS scene
    inside storage, so a render job can reuse it without re-reconstructing.
    """

    __tablename__ = "scenes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="Scene")
    mode: Mapped[str] = mapped_column(String(32), default="auto")
    reconstruction_status: Mapped[str] = mapped_column(String(40), default="created")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    scale_status: Mapped[str] = mapped_column(String(40), default="uncalibrated")
    coordinate_system: Mapped[str] = mapped_column(String(64), default="uncalibrated_local")
    unit: Mapped[str] = mapped_column(String(32), default="relative_units")
    representation_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    point_cloud_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    mesh_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_point: Mapped[list[float]] = mapped_column(JSON, default=lambda: [0.0, 0.0, 0.0])
    allowed_camera_bounds: Mapped[dict] = mapped_column(JSON, default=dict)
    camera_poses: Mapped[list[dict]] = mapped_column(JSON, default=list)
    asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    diagnostics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class RenderJob(Base):
    __tablename__ = "render_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    shot_id: Mapped[str | None] = mapped_column(ForeignKey("shots.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(32), default="preview")
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    state_machine_step: Mapped[str] = mapped_column(String(40), default="CREATED")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    fps: Mapped[int] = mapped_column(Integer)
    codec: Mapped[str] = mapped_column(String(32), default="h264")
    mode: Mapped[str] = mapped_column(String(32), default="auto")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    output_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AIJob(Base):
    __tablename__ = "ai_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    shot_id: Mapped[str | None] = mapped_column(ForeignKey("shots.id", ondelete="SET NULL"), nullable=True)
    module_name: Mapped[str] = mapped_column(String(64), default="wan2_2")
    model_id: Mapped[str] = mapped_column(String(120), default="Wan2.2-TI2V-5B")
    status: Mapped[str] = mapped_column(String(40), default="queued")
    prompt: Mapped[str] = mapped_column(Text, default="")
    seed: Mapped[int] = mapped_column(Integer, default=42)
    source_render_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_output_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    qc_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    user_decision: Mapped[str] = mapped_column(String(32), default="pending")
    qc_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="AI_ENHANCED — Hình ảnh được xử lý bởi mô hình AI, chỉ phục vụ minh họa trình chiếu, không phải hồ sơ kỹ thuật gốc.",
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

