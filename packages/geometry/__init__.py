"""
Geometry package — canonical coordinate transforms, keyframe extraction,
camera path schema, and Nerfstudio dataset adapter.

All coordinate transforms must go through coords.py.  Do NOT convert
elsewhere.
"""
from .coords import (
    colmap_to_canonical,
    canonical_to_colmap,
    canonical_to_nerfstudio,
    nerfstudio_to_canonical,
    CameraPose,
    VERSION as COORDS_VERSION,
)
from .camera_path import (
    CameraPathDocument,
    CameraKeyframeDoc,
    CameraPathError,
    SampledCamera,
    SCHEMA_VERSION,
)
from .keyframes import KeyframeSelector, KeyframeSelection, RegisteredView, DEFAULT_CONFIG as KEYFRAME_DEFAULT_CONFIG
from .nerfstudio import build_colmap_dataset, build_transforms, write_transforms

__all__ = [
    "colmap_to_canonical",
    "canonical_to_colmap",
    "canonical_to_nerfstudio",
    "nerfstudio_to_canonical",
    "COORDS_VERSION",
    "CameraPose",
    "CameraPathDocument",
    "CameraKeyframeDoc",
    "CameraPathError",
    "SampledCamera",
    "SCHEMA_VERSION",
    "KeyframeSelector",
    "KeyframeSelection",
    "RegisteredView",
    "KEYFRAME_DEFAULT_CONFIG",
    "build_colmap_dataset",
    "build_transforms",
    "write_transforms",
]
