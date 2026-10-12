"""Camera path schema + sampling (canonical, versioned).

A path document is the contract between the director/UI layer and every
renderer: keyframes carry **positions and quaternions** (never Euler angles),
the document samples to a deterministic camera sequence, and the same document
serialises to the nerfstudio ``camera-path`` JSON consumed by ``ns-render``.

Rules enforced here (SKILL_CANONICAL #14-#19):
    * rotation interpolation is quaternion SLERP only;
    * focal length interpolates independently and never zooms unless asked;
    * keyframe timestamps are strictly increasing;
    * ``catmull_rom`` positions use centripetal-style Catmull-Rom with
      configurable tension, ``cubic_bezier`` derives Bezier handles from the
      neighbour keyframes, ``linear`` stays linear.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from packages.camera_math import catmull_rom, cinematic_ease, lerp, normalize_quaternion, slerp

from .coords import CameraPose, canonical_to_nerfstudio

SCHEMA_VERSION = 1

EASINGS = ("linear", "ease_in", "ease_out", "ease_in_out", "cinematic")
PATH_TYPES = ("linear", "catmull_rom", "cubic_bezier")

DEFAULT_FOCAL_LENGTH_MM = 32.0
DEFAULT_SENSOR_WIDTH_MM = 36.0

MIN_FPS = 12
MAX_FPS = 60


class CameraPathError(ValueError):
    """Raised when a camera path document is not usable for rendering."""


def _ease(name: str, t: float) -> float:
    """Easing presets from SKILL_CANONICAL #16."""
    t = max(0.0, min(1.0, float(t)))
    if name == "linear":
        return t
    if name == "ease_in":
        return t * t
    if name == "ease_out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if name == "ease_in_out":
        return t * t * (3.0 - 2.0 * t)
    if name == "cinematic":
        return cinematic_ease(t)
    raise CameraPathError(f"unsupported easing {name!r}; expected one of {EASINGS}")


@dataclass(frozen=True)
class CameraKeyframeDoc:
    """One camera keyframe: a pose plus lens state at a point in time."""

    position: tuple[float, float, float]
    rotation_quaternion: tuple[float, float, float, float]
    timestamp_sec: float
    focal_length_mm: float = DEFAULT_FOCAL_LENGTH_MM
    sensor_width_mm: float = DEFAULT_SENSOR_WIDTH_MM
    confidence: float = 1.0
    locked: bool = False
    image_id: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", tuple(float(v) for v in self.position))
        object.__setattr__(
            self,
            "rotation_quaternion",
            normalize_quaternion(self.rotation_quaternion),
        )
        object.__setattr__(self, "timestamp_sec", float(self.timestamp_sec))

    def to_pose(self) -> CameraPose:
        return CameraPose(position=self.position, quaternion=self.rotation_quaternion)

    @classmethod
    def from_pose(
        cls,
        pose: CameraPose,
        timestamp_sec: float,
        **kwargs,
    ) -> "CameraKeyframeDoc":
        return cls(
            position=pose.position,
            rotation_quaternion=pose.quaternion,
            timestamp_sec=timestamp_sec,
            **kwargs,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image_id": self.image_id,
            "position": list(self.position),
            "rotation_quaternion": list(self.rotation_quaternion),
            "quaternion_order": "xyzw",
            "timestamp_sec": self.timestamp_sec,
            "focal_length_mm": self.focal_length_mm,
            "sensor_width_mm": self.sensor_width_mm,
            "confidence": self.confidence,
            "locked": self.locked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CameraKeyframeDoc":
        return cls(
            position=tuple(data["position"]),
            rotation_quaternion=tuple(data["rotation_quaternion"]),
            timestamp_sec=data["timestamp_sec"],
            focal_length_mm=data.get("focal_length_mm", DEFAULT_FOCAL_LENGTH_MM),
            sensor_width_mm=data.get("sensor_width_mm", DEFAULT_SENSOR_WIDTH_MM),
            confidence=data.get("confidence", 1.0),
            locked=data.get("locked", False),
            image_id=data.get("image_id"),
            id=data.get("id", ""),
        )


@dataclass(frozen=True)
class SampledCamera:
    """A camera state produced by sampling a path (one rendered frame)."""

    timestamp_sec: float
    position: tuple[float, float, float]
    rotation_quaternion: tuple[float, float, float, float]
    focal_length_mm: float
    sensor_width_mm: float

    @property
    def pose(self) -> CameraPose:
        return CameraPose(position=self.position, quaternion=self.rotation_quaternion)

    def vertical_fov_deg(self, aspect: float) -> float:
        """Vertical field of view in degrees (nerfstudio ``fov`` is vertical).

        ``aspect`` is ``width / height``; the horizontal half-angle is scaled by
        ``height / width`` to obtain the vertical half-angle.
        """
        if self.focal_length_mm <= 0.0:
            raise CameraPathError("focal_length_mm must be positive")
        if aspect <= 0.0:
            raise CameraPathError("aspect (width / height) must be positive")
        half_x = math.atan(self.sensor_width_mm / (2.0 * self.focal_length_mm))
        return math.degrees(2.0 * math.atan(math.tan(half_x) / aspect))

    def to_dict(self) -> dict:
        return {
            "timestamp_sec": self.timestamp_sec,
            "position": list(self.position),
            "rotation_quaternion": list(self.rotation_quaternion),
            "focal_length_mm": self.focal_length_mm,
            "sensor_width_mm": self.sensor_width_mm,
        }


@dataclass
class CameraPathDocument:
    """Deterministic, serialisable camera path for one shot."""

    keyframes: list[CameraKeyframeDoc]
    duration_sec: float
    fps: int = 30
    width: int = 1920
    height: int = 1080
    easing: str = "cinematic"
    path_type: str = "catmull_rom"
    tension: float = 0.5
    scene_id: str | None = None
    schema_version: int = SCHEMA_VERSION
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # validation
    # ------------------------------------------------------------------ #
    def problems(self) -> list[str]:
        issues: list[str] = []
        if self.schema_version != SCHEMA_VERSION:
            issues.append(f"schema_version {self.schema_version} != {SCHEMA_VERSION}")
        if len(self.keyframes) < 2:
            issues.append("a camera path needs at least 2 keyframes")
        if not (self.duration_sec > 0):
            issues.append("duration_sec must be positive")
        if self.fps < MIN_FPS or self.fps > MAX_FPS:
            issues.append(f"fps must be between {MIN_FPS} and {MAX_FPS}")
        if self.width <= 0 or self.height <= 0:
            issues.append("width and height must be positive")
        if self.easing not in EASINGS:
            issues.append(f"easing must be one of {EASINGS}")
        if self.path_type not in PATH_TYPES:
            issues.append(f"path_type must be one of {PATH_TYPES}")
        if not (0.0 <= self.tension <= 1.0):
            issues.append("tension must be within [0, 1]")

        previous = None
        for index, keyframe in enumerate(self.keyframes):
            if keyframe.focal_length_mm <= 0.0 or keyframe.sensor_width_mm <= 0.0:
                issues.append(f"keyframe {index}: focal/sensor values must be positive")
            if keyframe.timestamp_sec < 0.0:
                issues.append(f"keyframe {index}: timestamp_sec must be >= 0")
            if keyframe.timestamp_sec > self.duration_sec + 1e-6:
                issues.append(f"keyframe {index}: timestamp_sec exceeds duration_sec")
            if previous is not None and keyframe.timestamp_sec <= previous:
                issues.append(f"keyframe {index}: timestamps must be strictly increasing")
            previous = keyframe.timestamp_sec
        return issues

    def validate(self) -> "CameraPathDocument":
        issues = self.problems()
        if issues:
            raise CameraPathError("invalid camera path: " + "; ".join(issues))
        return self

    @property
    def frame_count(self) -> int:
        return max(2, int(round(self.duration_sec * self.fps)))

    # ------------------------------------------------------------------ #
    # sampling
    # ------------------------------------------------------------------ #
    def _segment(self, t: float) -> tuple[int, float]:
        """Return ``(lower_index, local_u)`` for absolute timeline position ``t``."""
        times = [k.timestamp_sec for k in self.keyframes]
        if t <= times[0]:
            return 0, 0.0
        if t >= times[-1]:
            return len(times) - 2, 1.0
        for i in range(len(times) - 1):
            if times[i] <= t <= times[i + 1]:
                span = times[i + 1] - times[i]
                return i, 0.0 if span <= 0 else (t - times[i]) / span
        return len(times) - 2, 1.0

    def _position(self, index: int, u: float) -> tuple[float, float, float]:
        points = [k.position for k in self.keyframes]
        p0 = points[max(0, index - 1)]
        p1 = points[index]
        p2 = points[min(len(points) - 1, index + 1)]
        p3 = points[min(len(points) - 1, index + 2)]
        if self.path_type == "linear":
            return lerp(p1, p2, u)  # type: ignore[return-value]
        if self.path_type == "cubic_bezier":
            c1 = tuple(a + (b - c) / 6.0 for a, b, c in zip(p1, p2, p0))
            c2 = tuple(a - (b - c) / 6.0 for a, b, c in zip(p2, p3, p1))
            return _cubic_bezier(p1, c1, c2, p2, u)
        return catmull_rom(p0, p1, p2, p3, u, tension=self.tension)  # type: ignore[return-value]

    def sample(self, t: float) -> SampledCamera:
        """Sample the path at absolute time ``t`` (seconds)."""
        self.validate()
        index, raw_u = self._segment(t)
        u = _ease(self.easing, raw_u)
        a = self.keyframes[index]
        b = self.keyframes[index + 1]
        return SampledCamera(
            timestamp_sec=max(0.0, min(self.duration_sec, t)),
            position=self._position(index, u),
            rotation_quaternion=slerp(a.rotation_quaternion, b.rotation_quaternion, u),
            focal_length_mm=float(lerp((a.focal_length_mm,), (b.focal_length_mm,), u)[0]),
            sensor_width_mm=float(lerp((a.sensor_width_mm,), (b.sensor_width_mm,), u)[0]),
        )

    def sample_sequence(self) -> list[SampledCamera]:
        """Sample ``frame_count`` cameras covering ``[0, duration_sec]``."""
        total = self.frame_count
        if total == 1:
            return [self.sample(0.0)]
        step = self.duration_sec / (total - 1)
        return [self.sample(min(self.duration_sec, i * step)) for i in range(total)]

    # ------------------------------------------------------------------ #
    # serialisation
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "scene_id": self.scene_id,
            "duration_sec": self.duration_sec,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "easing": self.easing,
            "path_type": self.path_type,
            "tension": self.tension,
            "metadata": dict(self.metadata),
            "keyframes": [k.to_dict() for k in self.keyframes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CameraPathDocument":
        return cls(
            keyframes=[CameraKeyframeDoc.from_dict(k) for k in data.get("keyframes", [])],
            duration_sec=float(data["duration_sec"]),
            fps=int(data.get("fps", 30)),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            easing=data.get("easing", "cinematic"),
            path_type=data.get("path_type", "catmull_rom"),
            tension=float(data.get("tension", 0.5)),
            scene_id=data.get("scene_id"),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            metadata=dict(data.get("metadata", {})),
        )

    # ------------------------------------------------------------------ #
    # nerfstudio adapter
    # ------------------------------------------------------------------ #
    def to_nerfstudio_camera_path(self) -> dict:
        """``ns-render camera-path --camera-path-filename`` payload.

        Poses are converted to nerfstudio's OpenGL camera convention through
        :func:`packages.geometry.coords.canonical_to_nerfstudio`; ``fov`` is the
        vertical field of view in degrees, which is what nerfstudio's
        ``PerspectiveCamera`` expects.
        """
        self.validate()
        aspect = self.width / self.height
        cameras = []
        for camera in self.sample_sequence():
            ns_pose = canonical_to_nerfstudio(camera.pose)
            cameras.append(
                {
                    "camera_to_world": [value for row in ns_pose.to_matrix() for value in row],
                    "fov": camera.vertical_fov_deg(aspect),
                    "aspect": aspect,
                }
            )
        return {
            "camera_type": "PerspectiveCamera",
            "render_height": self.height,
            "render_width": self.width,
            "fps": self.fps,
            "seconds": self.duration_sec,
            "camera_path": cameras,
            "is_cycle": False,
            "smoothness_value": 0.0,
            "default_fov": cameras[0]["fov"] if cameras else 0.0,
        }


def _cubic_bezier(
    p0: Sequence[float],
    c1: Sequence[float],
    c2: Sequence[float],
    p1: Sequence[float],
    u: float,
) -> tuple[float, float, float]:
    u = max(0.0, min(1.0, float(u)))
    v = 1.0 - u
    a = v * v * v
    b = 3.0 * v * v * u
    c = 3.0 * v * u * u
    d = u * u * u
    return tuple(  # type: ignore[return-value]
        a * x0 + b * x1 + c * x2 + d * x3 for x0, x1, x2, x3 in zip(p0, c1, c2, p1)
    )


__all__ = [
    "SCHEMA_VERSION",
    "EASINGS",
    "PATH_TYPES",
    "DEFAULT_FOCAL_LENGTH_MM",
    "DEFAULT_SENSOR_WIDTH_MM",
    "MIN_FPS",
    "MAX_FPS",
    "CameraPathError",
    "CameraKeyframeDoc",
    "SampledCamera",
    "CameraPathDocument",
]
