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
    template_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bgm_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sharpness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    exposure_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Shot(Base):
    __tablename__ = "shots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="Shot")
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mode: Mapped[str] = mapped_column(String(32), default="auto")
    camera_mode: Mapped[str] = mapped_column(String(32), default="2D_IMAGE_CAMERA")
    duration_sec: Mapped[float] = mapped_column(Float, default=5.0)
    fps: Mapped[int] = mapped_column(Integer, default=30)
    easing: Mapped[str] = mapped_column(String(32), default="cinematic")
    overlay_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    keyframes: Mapped[list[dict]] = mapped_column(JSON, default=list)
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
    representation_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
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
