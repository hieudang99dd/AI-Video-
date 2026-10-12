"""Scene helpers shared by the API layer and the worker.

Keeps scene/geometry DB bookkeeping in one place so routes stay thin and the
worker only orchestrates (SKILL_CANONICAL #55: contracts first, then worker
logic, then API).
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ImageAsset, Scene, Shot
from app.services.geometry_backend import GeometryQualityRejected, GeometrySceneResult
from app.services.storage import storage


def select_scene_for_shot(db: Session, shot: Shot) -> Scene | None:
    """Best scene for a shot: the one sharing the most assets with it."""
    scenes = list(db.scalars(select(Scene).where(Scene.project_id == shot.project_id)))
    shot_assets = set(shot.asset_ids or [])
    best: Scene | None = None
    best_overlap = 0
    for scene in scenes:
        overlap = len(set(scene.asset_ids or []) & shot_assets)
        if overlap > best_overlap:
            best, best_overlap = scene, overlap
    return best


def scene_asset_paths(db: Session, scene: Scene) -> list[Path]:
    """Resolve the immutable source images of a scene, preserving scene order."""
    asset_ids = list(scene.asset_ids or [])
    if not asset_ids:
        return []
    assets = list(db.scalars(select(ImageAsset).where(ImageAsset.id.in_(asset_ids))))
    by_id = {asset.id: asset for asset in assets}
    return [storage.resolve(by_id[asset_id].storage_uri) for asset_id in asset_ids if asset_id in by_id]


def scene_workdir(scene: Scene) -> Path:
    """Persistent reconstruction workspace (survives the job, reused by renders)."""
    return storage.resolve(f"local://projects/{scene.project_id}/scenes/{scene.id}")


def storage_uri_for(path: Path) -> str:
    """Convert an absolute path inside storage into a ``local://`` URI."""
    try:
        relative = Path(path).resolve().relative_to(storage.root.resolve())
    except ValueError as exc:
        raise ValueError(f"{path} is outside the storage root") from exc
    return f"local://{relative.as_posix()}"


def apply_reconstruction_success(scene: Scene, result: GeometrySceneResult) -> None:
    scene.reconstruction_status = "ready"
    scene.mode = "geometry"
    scene.confidence = float(result.metadata.get("geometry_confidence", 0.0))
    scene.representation_uri = storage_uri_for(Path(result.scene_uri))
    scene.diagnostics = {
        **dict(scene.diagnostics or {}),
        "backend": result.backend,
        "backend_version": result.backend_version,
        "registered_image_ratio": round(result.registered_image_ratio, 4),
        "camera_count": result.camera_count,
        "scene": result.metadata,
    }


def apply_reconstruction_rejection(scene: Scene, error: GeometryQualityRejected) -> None:
    scene.reconstruction_status = "rejected"
    scene.mode = "2.5d_lite"
    scene.confidence = float(error.metadata.get("geometry_confidence", 0.0))
    scene.representation_uri = None
    scene.diagnostics = {
        **dict(scene.diagnostics or {}),
        "rejection_reasons": list(error.reasons),
        "scene": error.metadata,
    }


def mark_reconstruction_failed(scene: Scene, message: str) -> None:
    scene.reconstruction_status = "failed"
    scene.diagnostics = {**dict(scene.diagnostics or {}), "error": message}


__all__ = [
    "select_scene_for_shot",
    "scene_asset_paths",
    "scene_workdir",
    "storage_uri_for",
    "apply_reconstruction_success",
    "apply_reconstruction_rejection",
    "mark_reconstruction_failed",
]
