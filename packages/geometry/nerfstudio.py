"""Nerfstudio adapters: dataset layout + ``transforms.json`` export.

Two independent adapters live here:

``build_colmap_dataset``
    Assembles the ``images/`` + ``colmap/sparse/0/`` layout that
    ``ns-train ... colmap --colmap-path sparse/0`` expects.  ``ns-train`` must
    never be pointed at a bare ``sparse`` folder (a bug in the pre-existing
    backend call), so the layout is built explicitly and returned.

``build_transforms`` / ``write_transforms``
    The generic nerfstudio/Blender ``transforms.json`` adapter (OpenGL camera
    convention, ``transform_matrix`` row-major) for the ``nerfstudio``
    dataparser and for exports.

Both adapters convert poses through :mod:`packages.geometry.coords` only.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .coords import CameraPose, canonical_to_nerfstudio
from .keyframes import RegisteredView

COLMAP_MODEL_FILES = ("cameras.txt", "images.txt", "points3D.txt", "cameras.bin", "images.bin", "points3D.bin")


def build_colmap_dataset(
    dataset_dir: Path,
    image_paths: Mapping[str, Path],
    sparse_model_dir: Path,
    *,
    copy_images: bool = True,
) -> Path:
    """Create ``dataset_dir/{images,colmap/sparse/0}`` and return ``dataset_dir``.

    ``image_paths`` maps the *registered* image name (as written in
    ``images.txt``) to the immutable source file.
    """
    images_dir = dataset_dir / "images"
    model_dir = dataset_dir / "colmap" / "sparse" / "0"
    images_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    for name, source in image_paths.items():
        if not source.exists():
            raise FileNotFoundError(f"source image missing: {source}")
        target = images_dir / name
        if copy_images:
            shutil.copy2(source, target)
        elif not target.exists():
            try:
                target.hardlink_to(source)
            except OSError:
                shutil.copy2(source, target)

    found = False
    for filename in COLMAP_MODEL_FILES:
        source = sparse_model_dir / filename
        if source.exists():
            shutil.copy2(source, model_dir / filename)
            found = True
    if not found:
        raise FileNotFoundError(
            f"no COLMAP model files found in {sparse_model_dir}; run `colmap model_converter --output_type TXT` first"
        )
    return dataset_dir


def build_transforms(
    views: Sequence[RegisteredView],
    width: int,
    height: int,
    *,
    focal_length_mm: float | None = None,
    sensor_width_mm: float | None = None,
    ply_file_path: str | None = None,
    camera_model: str = "perspective",
    extra_frames: Iterable[dict] = (),
) -> dict:
    """Nerfstudio ``transforms.json`` payload for registered views."""
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    frames = []
    for view in views:
        pose = canonical_to_nerfstudio(CameraPose(position=view.position, quaternion=view.quaternion))
        frames.append(
            {
                "file_path": f"images/{view.name}",
                "transform_matrix": [value for row in pose.to_matrix() for value in row],
                "colmap_im_id": view.image_id,
                "confidence": view.confidence,
            }
        )
    frames.extend(extra_frames)

    fx = _focal_pixels(
        focal_length_mm if focal_length_mm is not None else (views[0].focal_length_mm if views else 32.0),
        sensor_width_mm if sensor_width_mm is not None else (views[0].sensor_width_mm if views else 36.0),
        width,
    )
    payload = {
        "camera_model": camera_model,
        "fl_x": fx,
        "fl_y": fx,
        "cx": width / 2.0,
        "cy": height / 2.0,
        "w": width,
        "h": height,
        "k1": 0.0,
        "k2": 0.0,
        "p1": 0.0,
        "p2": 0.0,
        "frames": frames,
    }
    if ply_file_path:
        payload["ply_file_path"] = ply_file_path
    return payload


def write_transforms(dataset_dir: Path, transforms: Mapping) -> Path:
    """Write ``transforms.json`` into ``dataset_dir`` and return its path."""
    dataset_dir.mkdir(parents=True, exist_ok=True)
    target = dataset_dir / "transforms.json"
    with target.open("w", encoding="utf-8") as handle:
        json.dump(dict(transforms), handle, indent=2)
    return target


def _focal_pixels(focal_length_mm: float, sensor_width_mm: float, width: int) -> float:
    if focal_length_mm <= 0 or sensor_width_mm <= 0:
        raise ValueError("focal length and sensor width must be positive")
    return focal_length_mm / sensor_width_mm * float(width)


__all__ = [
    "COLMAP_MODEL_FILES",
    "build_colmap_dataset",
    "build_transforms",
    "write_transforms",
]
