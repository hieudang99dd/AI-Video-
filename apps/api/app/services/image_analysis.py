from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageOps
import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def analyze_image(path: Path) -> dict:
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError("unsupported image format")

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        width, height = img.size
        arr = np.asarray(img)

    gray = arr.mean(axis=2).astype(np.float32)
    exposure = float(gray.mean() / 255.0)

    if cv2 is not None:
        sharpness = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    else:
        dx = np.diff(gray, axis=1)
        dy = np.diff(gray, axis=0)
        sharpness = float((dx.var() + dy.var()) / 2)

    return {
        "width": width,
        "height": height,
        "exposure_score": round(exposure, 4),
        "sharpness_score": round(sharpness, 4),
    }


def select_mode(asset_count: int, geometry_available: bool) -> str:
    if asset_count <= 1:
        return "2.5d_lite"
    if asset_count >= 3 and geometry_available:
        return "geometry"
    if asset_count >= 2:
        return "transition"
    return "2.5d_lite"
