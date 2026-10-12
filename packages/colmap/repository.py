"""COLMAP model repository.

Reads a COLMAP sparse model (``cameras.txt`` / ``images.txt`` /
``points3D.txt``, produced by ``colmap model_converter --output_type TXT``) and
the match statistics stored in ``database.db`` — using only ``stdlib`` +
``sqlite3`` so the repository stays usable without PyCOLMAP.

All pose conversions go through :mod:`packages.geometry.coords`; this module
never converts frames itself.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from packages.geometry.camera_path import DEFAULT_FOCAL_LENGTH_MM, DEFAULT_SENSOR_WIDTH_MM
from packages.geometry.coords import CameraPose, points_to_canonical, pose_from_colmap
from packages.geometry.keyframes import RegisteredView

DEFAULT_SCENE_CONFIG: dict = {
    "min_registered_ratio": 0.6,
    "max_mean_reprojection_error": 2.0,
    "geometry_confidence_threshold": 0.75,
    "min_camera_count": 3,
    "min_baseline_ratio": 0.15,
}

_MODEL_INTRINSIC_LAYOUT: dict[str, tuple[int, int, int, int]] = {
    "SIMPLE_PINHOLE": (0, 0, 1, 2),
    "PINHOLE": (0, 1, 2, 3),
    "SIMPLE_RADIAL": (0, 0, 1, 2),
    "RADIAL": (0, 0, 1, 2),
    "OPENCV": (0, 1, 2, 3),
    "OPENCV_FISHEYE": (0, 1, 2, 3),
    "FULL_OPENCV": (0, 1, 2, 3),
}


@dataclass(frozen=True)
class ColmapCamera:
    """One COLMAP camera (intrinsics)."""

    id: int
    model: str
    width: int
    height: int
    params: tuple[float, ...]

    def intrinsics(self) -> tuple[float, float, float, float]:
        """``(fx, fy, cx, cy)`` in pixels."""
        layout = _MODEL_INTRINSIC_LAYOUT.get(self.model.upper())
        if layout is None:
            raise ValueError(
                f"unsupported COLMAP camera model {self.model!r}; "
                f"supported: {sorted(_MODEL_INTRINSIC_LAYOUT)}"
            )
        fx_i, fy_i, cx_i, cy_i = layout
        if len(self.params) <= max(layout):
            raise ValueError(f"camera {self.id}: expected at least {max(layout) + 1} params for {self.model}")
        return (
            float(self.params[fx_i]),
            float(self.params[fy_i]),
            float(self.params[cx_i]),
            float(self.params[cy_i]),
        )

    def focal_length_mm(self, sensor_width_mm: float = DEFAULT_SENSOR_WIDTH_MM) -> float:
        fx, _, _, _ = self.intrinsics()
        if self.width <= 0:
            raise ValueError(f"camera {self.id}: width must be positive")
        return fx / float(self.width) * sensor_width_mm

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model": self.model,
            "width": self.width,
            "height": self.height,
            "params": list(self.params),
        }


@dataclass(frozen=True)
class ColmapImage:
    """One registered image with its COLMAP world-to-camera pose."""

    id: int
    name: str
    qvec: tuple[float, float, float, float]
    tvec: tuple[float, float, float]
    camera_id: int
    num_points2d: int = 0
    num_points3d: int = 0

    def canonical_pose(self, up_axis: str = "z") -> CameraPose:
        return pose_from_colmap(self.qvec, self.tvec, up_axis=up_axis)

    def camera_center(self, up_axis: str = "z") -> tuple[float, float, float]:
        return self.canonical_pose(up_axis=up_axis).position

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "camera_id": self.camera_id,
            "qvec": list(self.qvec),
            "tvec": list(self.tvec),
            "qvec_order": "wxyz",
            "num_points2d": self.num_points2d,
            "num_points3d": self.num_points3d,
        }


@dataclass(frozen=True)
class ColmapPoint3D:
    id: int
    xyz: tuple[float, float, float]
    rgb: tuple[int, int, int]
    error: float
    image_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class VerifiedPair:
    """A geometrically verified image pair from ``two_view_geometries``."""

    image_id1: int
    image_id2: int
    inlier_count: int
    match_count: int = 0

    @property
    def inlier_ratio(self) -> float:
        if self.match_count <= 0:
            return 0.0
        return min(1.0, self.inlier_count / float(self.match_count))

    def to_dict(self) -> dict:
        return {
            "image_id1": self.image_id1,
            "image_id2": self.image_id2,
            "inlier_count": self.inlier_count,
            "match_count": self.match_count,
            "inlier_ratio": round(self.inlier_ratio, 4),
        }


@dataclass
class ColmapSceneData:
    """Parsed sparse model plus derived scene statistics."""

    sparse_dir: Path
    cameras: dict[int, ColmapCamera] = field(default_factory=dict)
    images: dict[int, ColmapImage] = field(default_factory=dict)
    points3d: dict[int, ColmapPoint3D] = field(default_factory=dict)
    verified_pairs: list[VerifiedPair] = field(default_factory=list)
    up_axis: str = "z"
    expected_image_count: int | None = None
    diagnostics: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # statistics
    # ------------------------------------------------------------------ #
    @property
    def registered_image_count(self) -> int:
        return len(self.images)

    @property
    def registered_ratio(self) -> float:
        expected = self.expected_image_count or self.registered_image_count
        if expected <= 0:
            return 0.0
        return min(1.0, self.registered_image_count / float(expected))

    @property
    def mean_reprojection_error(self) -> float:
        if not self.points3d:
            return 0.0
        return sum(p.error for p in self.points3d.values()) / len(self.points3d)

    @property
    def mean_track_length(self) -> float:
        if not self.points3d:
            return 0.0
        return sum(len(p.image_ids) for p in self.points3d.values()) / len(self.points3d)

    def camera_centers(self) -> list[tuple[float, float, float]]:
        return [image.camera_center(up_axis=self.up_axis) for image in self.images.values()]

    def canonical_points(self, limit: int | None = None) -> list[tuple[float, float, float]]:
        """Sparse cloud mapped into the canonical frame (matches ``camera_centers``)."""
        points = points_to_canonical([p.xyz for p in self.points3d.values()], up_axis=self.up_axis)
        if limit is not None and limit > 0 and len(points) > limit:
            stride = max(1, len(points) // limit)
            points = points[::stride]
        return points

    def scene_extent(self) -> float:
        return _max_pairwise(self.camera_centers())

    def registered_views(self) -> list[RegisteredView]:
        """Canonical :class:`RegisteredView` list for keyframe selection."""
        if not self.images:
            return []
        median_points = _median([image.num_points3d for image in self.images.values()])
        reference = median_points if median_points > 0 else 1.0
        views: list[RegisteredView] = []
        for image in self.images.values():
            camera = self.cameras.get(image.camera_id)
            pose = image.canonical_pose(up_axis=self.up_axis)
            views.append(
                RegisteredView(
                    image_id=str(image.id),
                    name=image.name,
                    position=pose.position,
                    quaternion=pose.quaternion,
                    confidence=_image_confidence(image.num_points3d / reference, self.mean_reprojection_error),
                    focal_length_mm=(
                        camera.focal_length_mm() if camera is not None else DEFAULT_FOCAL_LENGTH_MM
                    ),
                    sensor_width_mm=DEFAULT_SENSOR_WIDTH_MM,
                )
            )
        return views

    def geometry_confidence(self) -> float:
        """Blend of registration, reprojection, baseline and match evidence (0..1)."""
        components: list[tuple[float, float]] = [
            (self.registered_ratio, 0.45),
            (_reprojection_score(self.mean_reprojection_error), 0.25),
            (_baseline_score(self.camera_centers()), 0.15),
        ]
        if self.verified_pairs:
            ratios = [pair.inlier_ratio for pair in self.verified_pairs]
            components.append((sum(ratios) / len(ratios), 0.15))
        total_weight = sum(weight for _, weight in components)
        if total_weight <= 0:
            return 0.0
        score = sum(value * weight for value, weight in components) / total_weight
        return max(0.0, min(1.0, score))

    def quality_gate(self, config: dict | None = None) -> tuple[bool, list[str]]:
        """Apply the Phase 0 scene gate; returns ``(passed, reasons)``."""
        merged = dict(DEFAULT_SCENE_CONFIG)
        merged.update(config or {})
        reasons: list[str] = []
        if self.registered_image_count < merged["min_camera_count"]:
            reasons.append(
                f"only {self.registered_image_count} cameras registered "
                f"(needs >= {merged['min_camera_count']})"
            )
        if self.registered_ratio < merged["min_registered_ratio"]:
            reasons.append(
                f"registered ratio {self.registered_ratio:.2f} < {merged['min_registered_ratio']}"
            )
        if self.mean_reprojection_error > merged["max_mean_reprojection_error"]:
            reasons.append(
                f"mean reprojection error {self.mean_reprojection_error:.3f}px > "
                f"{merged['max_mean_reprojection_error']}px"
            )
        centers = self.camera_centers()
        if len(centers) >= 2 and _baseline_score(centers) < merged["min_baseline_ratio"]:
            reasons.append("camera baseline too small for a trustworthy camera path")
        confidence = self.geometry_confidence()
        if confidence < merged["geometry_confidence_threshold"]:
            reasons.append(
                f"geometry confidence {confidence:.2f} < {merged['geometry_confidence_threshold']}"
            )
        return (not reasons), reasons

    def to_dict(self) -> dict:
        passed, reasons = self.quality_gate()
        return {
            "sparse_dir": str(self.sparse_dir),
            "up_axis": self.up_axis,
            "camera_count": len(self.cameras),
            "registered_image_count": self.registered_image_count,
            "expected_image_count": self.expected_image_count,
            "registered_ratio": round(self.registered_ratio, 4),
            "point_count": len(self.points3d),
            "mean_reprojection_error": round(self.mean_reprojection_error, 4),
            "mean_track_length": round(self.mean_track_length, 4),
            "scene_extent": round(self.scene_extent(), 4),
            "verified_pair_count": len(self.verified_pairs),
            "geometry_confidence": round(self.geometry_confidence(), 4),
            "quality_gate": {"passed": passed, "reasons": reasons},
            "diagnostics": dict(self.diagnostics),
        }


class ColmapRepository:
    """Read-only access to a COLMAP sparse model directory."""

    def __init__(
        self,
        sparse_dir: Path,
        expected_image_count: int | None = None,
        up_axis: str = "z",
    ) -> None:
        self.sparse_dir = Path(sparse_dir)
        self.expected_image_count = expected_image_count
        self.up_axis = up_axis

    def available_model_files(self) -> list[str]:
        if not self.sparse_dir.exists():
            return []
        return sorted(p.name for p in self.sparse_dir.iterdir() if p.is_file())

    def load(self) -> ColmapSceneData:
        """Parse the text model; raises actionable errors when it is missing."""
        images_txt = self.sparse_dir / "images.txt"
        images_bin = self.sparse_dir / "images.bin"
        if not images_txt.exists() and images_bin.exists():
            raise RuntimeError(
                f"binary COLMAP model found in {self.sparse_dir}; run "
                "`colmap model_converter --output_path <dir> --output_type TXT` first"
            )
        if not images_txt.exists():
            raise FileNotFoundError(
                f"no COLMAP text model in {self.sparse_dir} "
                "(looked for cameras.txt/images.txt/points3D.txt)"
            )

        diagnostics: dict = {"model_files": self.available_model_files()}
        cameras = self.parse_cameras(self.sparse_dir / "cameras.txt")
        images = self.parse_images(images_txt)
        points = self.parse_points3d(self.sparse_dir / "points3D.txt")
        database = self.sparse_dir.parent.parent / "database.db"
        verified: list[VerifiedPair] = []
        if database.exists():
            verified = self.read_verified_pairs(database)
            diagnostics["database"] = str(database)
        else:
            diagnostics["database"] = None
            diagnostics["verified_pairs"] = "database.db not found; inlier evidence unavailable"

        return ColmapSceneData(
            sparse_dir=self.sparse_dir,
            cameras=cameras,
            images=images,
            points3d=points,
            verified_pairs=verified,
            up_axis=self.up_axis,
            expected_image_count=self.expected_image_count,
            diagnostics=diagnostics,
        )

    # ------------------------------------------------------------------ #
    # parsers
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_cameras(path: Path) -> dict[int, ColmapCamera]:
        cameras: dict[int, ColmapCamera] = {}
        if not path.exists():
            return cameras
        for line in _data_lines(path):
            parts = line.split()
            if len(parts) < 5:
                continue
            cameras[int(parts[0])] = ColmapCamera(
                id=int(parts[0]),
                model=parts[1],
                width=int(parts[2]),
                height=int(parts[3]),
                params=tuple(float(v) for v in parts[4:]),
            )
        return cameras

    @staticmethod
    def parse_images(path: Path) -> dict[int, ColmapImage]:
        """Parse ``images.txt`` (two lines per image: pose line + 2D point line).

        The image name is the last COLMAP field and may contain spaces, so the
        pose line is split into at most 10 fields.
        """
        images: dict[int, ColmapImage] = {}
        lines = _data_lines(path, keep_blanks=True)
        index = 0
        while index < len(lines):
            parts = lines[index].split(None, 9)
            index += 1
            if len(parts) < 10:
                continue
            num_points2d, num_points3d = 0, 0
            if index < len(lines):
                track = lines[index].split()
                index += 1
                num_points2d = len(track) // 3
                num_points3d = sum(
                    1 for i in range(2, len(track), 3) if int(track[i]) != -1
                )
            images[int(parts[0])] = ColmapImage(
                id=int(parts[0]),
                name=parts[9],
                qvec=(float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])),
                tvec=(float(parts[5]), float(parts[6]), float(parts[7])),
                camera_id=int(parts[8]),
                num_points2d=num_points2d,
                num_points3d=num_points3d,
            )
        return images

    @staticmethod
    def parse_points3d(path: Path) -> dict[int, ColmapPoint3D]:
        points: dict[int, ColmapPoint3D] = {}
        if not path.exists():
            return points
        for line in _data_lines(path):
            parts = line.split()
            if len(parts) < 8:
                continue
            track = parts[8:]
            image_ids = tuple(int(track[i]) for i in range(0, len(track) - 1, 2))
            points[int(parts[0])] = ColmapPoint3D(
                id=int(parts[0]),
                xyz=(float(parts[1]), float(parts[2]), float(parts[3])),
                rgb=(int(parts[4]), int(parts[5]), int(parts[6])),
                error=float(parts[7]),
                image_ids=image_ids,
            )
        return points

    @staticmethod
    def read_verified_pairs(database_path: Path, min_inliers: int = 1) -> list[VerifiedPair]:
        """Read geometrically verified pairs from ``database.db`` via sqlite3."""
        pair_inliers = _read_pair_counts(database_path, "two_view_geometries")
        pair_matches = _read_pair_counts(database_path, "matches")
        pairs: list[VerifiedPair] = []
        for pair_id, inliers in pair_inliers.items():
            if inliers < min_inliers:
                continue
            image_id1, image_id2 = _decode_pair_id(pair_id)
            pairs.append(
                VerifiedPair(
                    image_id1=image_id1,
                    image_id2=image_id2,
                    inlier_count=inliers,
                    match_count=pair_matches.get(pair_id, inliers),
                )
            )
        pairs.sort(key=lambda p: (-p.inlier_count, p.image_id1, p.image_id2))
        return pairs


# --------------------------------------------------------------------------- #
# module helpers
# --------------------------------------------------------------------------- #
def _data_lines(path: Path, keep_blanks: bool = False) -> list[str]:
    """Return non-comment lines of a COLMAP text file."""
    if not path.exists():
        return []
    result: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            continue
        if not line and not keep_blanks:
            continue
        result.append(line)
    return result


def _read_pair_counts(database_path: Path, table: str) -> dict[int, int]:
    """Read ``(pair_id, rows)`` from a COLMAP database table (read-only)."""
    try:
        connection = sqlite3.connect(f"file:{Path(database_path).as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:  # pragma: no cover - depends on sqlite build
        raise RuntimeError(f"cannot open COLMAP database {database_path}: {exc}") from exc
    try:
        cursor = connection.execute(f"SELECT pair_id, rows FROM {table}")
        return {int(pair_id): int(rows) for pair_id, rows in cursor.fetchall()}
    except sqlite3.Error as exc:
        raise RuntimeError(
            f"COLMAP database {database_path} has no readable {table} table: {exc}"
        ) from exc
    finally:
        connection.close()


def _decode_pair_id(pair_id: int) -> tuple[int, int]:
    """COLMAP encodes pair ids as ``image_id1 * 2147483647 + image_id2``."""
    image_id2 = pair_id % 2147483647
    image_id1 = (pair_id - image_id2) // 2147483647
    return image_id1, image_id2


def _max_pairwise(points: Iterable[Sequence[float]]) -> float:
    items = [tuple(float(v) for v in p) for p in points]
    best = 0.0
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            best = max(best, math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))))
    return best


def _mean_pairwise(points: Sequence[Sequence[float]]) -> float:
    items = [tuple(float(v) for v in p) for p in points]
    distances = [
        math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        for i, a in enumerate(items)
        for b in items[i + 1:]
    ]
    if not distances:
        return 0.0
    return sum(distances) / len(distances)


def _median(values: Iterable[float]) -> float:
    items = sorted(float(v) for v in values)
    if not items:
        return 0.0
    middle = len(items) // 2
    if len(items) % 2:
        return items[middle]
    return (items[middle - 1] + items[middle]) / 2.0


def _reprojection_score(mean_error_px: float) -> float:
    """1.0 for <= 0.5px, decaying to 0.0 at 2.5px (starting value, needs calibration)."""
    if mean_error_px <= 0.5:
        return 1.0
    return max(0.0, 1.0 - (mean_error_px - 0.5) / 2.0)


def _baseline_score(centers: Sequence[Sequence[float]]) -> float:
    """How spread the camera rig is: 0 when clustered, 1 when max/mean >= 1.5."""
    if len(centers) < 2:
        return 0.0
    mean_distance = _mean_pairwise(centers)
    if mean_distance <= 0.0:
        return 0.0
    ratio = _max_pairwise(centers) / mean_distance
    return max(0.0, min(1.0, (ratio - 1.0) / 0.5))


def _image_confidence(point_ratio: float, mean_error_px: float) -> float:
    """Heuristic per-image confidence from track density and reprojection error."""
    base = max(0.0, min(1.0, point_ratio))
    score = 0.6 * base + 0.4 * _reprojection_score(mean_error_px)
    return max(0.0, min(1.0, score))


__all__ = [
    "DEFAULT_SCENE_CONFIG",
    "ColmapCamera",
    "ColmapImage",
    "ColmapPoint3D",
    "VerifiedPair",
    "ColmapSceneData",
    "ColmapRepository",
]
