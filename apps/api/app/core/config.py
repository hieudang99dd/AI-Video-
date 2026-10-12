from __future__ import annotations

import tempfile
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_tmp = Path(tempfile.gettempdir())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = f"sqlite:///{(_tmp / 'cinevideo.db').as_posix()}"
    redis_url: str | None = None
    storage_backend: str = "local"
    storage_root: Path = _tmp / "cinevideo-storage"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    colmap_path: str = "colmap"
    ns_train_path: str = "ns-train"
    ns_render_path: str = "ns-render"
    ns_train_iterations: int = 7000
    geometry_backend: str = "capability_gated"

    # Reconstruction thresholds (SKILL_CANONICAL #56 — starting values, calibrate
    # with the Phase 0 benchmark datasets before trusting them in production).
    min_images_geometry: int = 3
    min_registered_ratio: float = 0.6
    geometry_confidence_threshold: float = 0.75
    max_mean_reprojection_error_px: float = 2.0
    colmap_up_axis: str = "z"
    colmap_feature_matcher: str = "exhaustive"
    colmap_camera_model: str = "SIMPLE_RADIAL"
    colmap_sift_use_gpu: bool = False

    # Camera / path quality gates.
    max_angular_velocity_deg_sec: float = 45.0
    max_focal_change_ratio: float = 0.35
    min_render_score: float = 0.65
    max_artifact_risk: float = 0.35
    max_keyframes: int = 3

    render_preview_width: int = 1280
    render_preview_height: int = 720
    render_final_width: int = 1920
    render_final_height: int = 1080
    render_default_fps: int = 30
    render_max_duration_sec: float = 30.0


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
