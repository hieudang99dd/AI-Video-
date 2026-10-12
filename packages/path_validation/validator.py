"""Camera path validation (SKILL_CANONICAL #19, #20, #21, #36).

A path is sampled, scored and **rejected** when it violates a hard rule:

    * camera leaves the reconstruction bounds / enters the geometry proxy;
    * rotation velocity or focal change is too large (jerky, artifact-prone);
    * novel-view confidence collapses (camera far outside the training views);
    * the weighted score falls under ``min_score``.

``score`` is a weighted blend of smoothness, clearance, visibility and geometry
confidence.  Weights and thresholds are *starting values* that must be
calibrated with the benchmark datasets (SKILL_CANONICAL "Quy ước về ngưỡng số
liệu") — they live in :data:`DEFAULT_CONFIG`, never inline in feature code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence

from packages.geometry.camera_path import DEFAULT_FOCAL_LENGTH_MM, DEFAULT_SENSOR_WIDTH_MM
from packages.geometry.coords import rotation_angle_deg

DEFAULT_CONFIG: dict = {
    "sample_count": 60,
    "min_samples": 2,
    "min_clearance_m": 0.25,
    "near_clearance_m": 0.6,
    "max_angular_velocity_deg_sec": 45.0,
    "max_focal_change_ratio": 0.35,
    "max_speed_m_s": 4.0,
    "min_score": 0.65,
    "weights": {
        "smoothness": 0.25,
        "clearance": 0.2,
        "visibility": 0.3,
        "geometry": 0.25,
    },
    "reject_on_collision": True,
    "reject_on_out_of_bounds": True,
}

Vector3 = tuple[float, float, float]


class ClearanceStatus(str, Enum):
    """Per-sample clearance verdict."""

    OK = "ok"
    NEAR = "near"
    COLLISION = "collision"
    OUT_OF_BOUNDS = "out_of_bounds"
    UNKNOWN = "unknown"


class SceneProxy(Protocol):
    """Geometry proxy the validator queries (sparse points, occupancy, mesh...)."""

    def query_clearance(self, position: Sequence[float]) -> float | None: ...

    def view_confidence(self, position: Sequence[float]) -> float | None: ...

    def in_bounds(self, position: Sequence[float]) -> bool | None: ...


@dataclass(frozen=True)
class CameraSample:
    """One sampled camera state (``camera_path.SampledCamera`` is compatible)."""

    timestamp_sec: float
    position: Vector3
    rotation_quaternion: tuple[float, float, float, float]
    focal_length_mm: float = DEFAULT_FOCAL_LENGTH_MM
    sensor_width_mm: float = DEFAULT_SENSOR_WIDTH_MM
    confidence: float | None = None

    @classmethod
    def from_camera(cls, camera) -> "CameraSample":
        """Adapt any object exposing the camera-path sampling attributes."""
        return cls(
            timestamp_sec=float(getattr(camera, "timestamp_sec")),
            position=tuple(float(v) for v in getattr(camera, "position")),  # type: ignore[arg-type]
            rotation_quaternion=tuple(  # type: ignore[arg-type]
                float(v) for v in getattr(camera, "rotation_quaternion")
            ),
            focal_length_mm=float(getattr(camera, "focal_length_mm", DEFAULT_FOCAL_LENGTH_MM)),
            sensor_width_mm=float(getattr(camera, "sensor_width_mm", DEFAULT_SENSOR_WIDTH_MM)),
            confidence=getattr(camera, "confidence", None),
        )

    @classmethod
    def from_sequence(cls, cameras: Sequence) -> list["CameraSample"]:
        return [c if isinstance(c, cls) else cls.from_camera(c) for c in cameras]


@dataclass(frozen=True)
class SampleResult:
    """Per-sample validation detail, kept for telemetry/debug overlays."""

    timestamp_sec: float
    position: Vector3
    clearance_m: float | None
    status: ClearanceStatus
    angular_velocity_deg_sec: float
    speed_m_s: float
    view_score: float | None
    focal_change_ratio: float

    def to_dict(self) -> dict:
        return {
            "timestamp_sec": self.timestamp_sec,
            "position": list(self.position),
            "clearance_m": self.clearance_m,
            "status": self.status.value,
            "angular_velocity_deg_sec": round(self.angular_velocity_deg_sec, 4),
            "speed_m_s": round(self.speed_m_s, 4),
            "view_score": self.view_score,
            "focal_change_ratio": round(self.focal_change_ratio, 4),
        }


@dataclass(frozen=True)
class PathValidationResult:
    """Validation verdict for one camera path."""

    ok: bool
    score: float
    rejection_reasons: tuple[str, ...] = ()
    samples: tuple[SampleResult, ...] = ()
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "score": round(self.score, 4),
            "rejection_reasons": list(self.rejection_reasons),
            "metrics": dict(self.metrics),
            "samples": [s.to_dict() for s in self.samples],
        }


# --------------------------------------------------------------------------- #
# geometry proxies
# --------------------------------------------------------------------------- #
@dataclass
class PointCloudProxy:
    """Clearance/visibility proxy built from a sparse point cloud + camera views."""

    points: list[Vector3] = field(default_factory=list)
    training_positions: list[Vector3] = field(default_factory=list)
    bounds: tuple[Vector3, Vector3] | None = None
    max_view_distance: float | None = None

    def __post_init__(self) -> None:
        self.points = [tuple(float(v) for v in p) for p in self.points]  # type: ignore[misc]
        self.training_positions = [  # type: ignore[misc]
            tuple(float(v) for v in p) for p in self.training_positions
        ]
        if self.max_view_distance is None:
            spread = _max_pairwise(self.training_positions) if len(self.training_positions) > 1 else 0.0
            self.max_view_distance = max(1e-3, spread)

    def query_clearance(self, position: Sequence[float]) -> float | None:
        if not self.points:
            return None
        return min(_distance(position, point) for point in self.points)

    def view_confidence(self, position: Sequence[float]) -> float | None:
        """1.0 near a training view, decaying to 0.0 past ``max_view_distance``."""
        if not self.training_positions:
            return None
        nearest = min(_distance(position, view) for view in self.training_positions)
        limit = float(self.max_view_distance or 0.0)
        if limit <= 0.0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - nearest / limit))

    def in_bounds(self, position: Sequence[float]) -> bool | None:
        if self.bounds is None:
            return None
        low, high = self.bounds
        return all(lo - 1e-9 <= value <= hi + 1e-9 for value, lo, hi in zip(position, low, high))

    @classmethod
    def from_sampled_cloud(
        cls,
        points: Sequence[Sequence[float]],
        training_positions: Sequence[Sequence[float]],
        margin_ratio: float = 0.25,
    ) -> "PointCloudProxy":
        """Build a proxy with an AABB expanded by ``margin_ratio`` of its diagonal.

        The AABB covers the sparse points **and** the training camera centres:
        cameras normally sit outside the reconstructed surface, so a points-only
        box would flag every legitimate camera position as out of bounds.
        """
        pts = [tuple(float(v) for v in p) for p in points]
        views = [tuple(float(v) for v in p) for p in training_positions]
        bounds = None
        volume = pts + views
        if volume:
            low = tuple(min(p[i] for p in volume) for i in range(3))
            high = tuple(max(p[i] for p in volume) for i in range(3))
            margin = math.dist(low, high) * max(0.0, margin_ratio)
            bounds = (
                tuple(low[i] - margin for i in range(3)),  # type: ignore[arg-type]
                tuple(high[i] + margin for i in range(3)),  # type: ignore[arg-type]
            )
        return cls(points=pts, training_positions=views, bounds=bounds)


@dataclass
class BoundsProxy:
    """Proxy with bounds only (no clearance/visibility evidence)."""

    bounds: tuple[Vector3, Vector3] | None = None

    def query_clearance(self, position: Sequence[float]) -> float | None:
        return None

    def view_confidence(self, position: Sequence[float]) -> float | None:
        return None

    def in_bounds(self, position: Sequence[float]) -> bool | None:
        if self.bounds is None:
            return None
        low, high = self.bounds
        return all(lo - 1e-9 <= value <= hi + 1e-9 for value, lo, hi in zip(position, low, high))


# --------------------------------------------------------------------------- #
# validator
# --------------------------------------------------------------------------- #
class PathValidator:
    """Scores and gates a sampled camera path before any final render."""

    def __init__(self, config: dict | None = None) -> None:
        merged = dict(DEFAULT_CONFIG)
        merged.update(config or {})
        weights = dict(DEFAULT_CONFIG["weights"])
        weights.update((config or {}).get("weights", {}))
        merged["weights"] = weights
        self.config = merged

    def validate(self, cameras: Sequence, proxy: SceneProxy | None = None) -> PathValidationResult:
        samples = CameraSample.from_sequence(cameras)
        reasons: list[str] = []
        if len(samples) < self.config["min_samples"]:
            return PathValidationResult(
                ok=False,
                score=0.0,
                rejection_reasons=("not_enough_samples",),
                samples=(),
                metrics={"sample_count": len(samples)},
            )

        focal_reference = samples[0].focal_length_mm or DEFAULT_FOCAL_LENGTH_MM
        results: list[SampleResult] = []
        for index, sample in enumerate(samples):
            angular_velocity = 0.0
            speed = 0.0
            if index > 0:
                previous = samples[index - 1]
                delta_t = sample.timestamp_sec - previous.timestamp_sec
                if delta_t <= 0.0:
                    reasons.append("non_monotonic_time")
                    delta_t = 0.0
                if delta_t > 0.0:
                    angular_velocity = (
                        rotation_angle_deg(previous.rotation_quaternion, sample.rotation_quaternion)
                        / delta_t
                    )
                    speed = _distance(previous.position, sample.position) / delta_t
            focal_ratio = (
                abs(sample.focal_length_mm - focal_reference) / focal_reference
                if focal_reference > 0
                else 0.0
            )
            clearance = proxy.query_clearance(sample.position) if proxy is not None else None
            in_bounds = proxy.in_bounds(sample.position) if proxy is not None else None
            view_score = proxy.view_confidence(sample.position) if proxy is not None else None
            results.append(
                SampleResult(
                    timestamp_sec=sample.timestamp_sec,
                    position=sample.position,
                    clearance_m=clearance,
                    status=self._status(clearance, in_bounds),
                    angular_velocity_deg_sec=angular_velocity,
                    speed_m_s=speed,
                    view_score=view_score,
                    focal_change_ratio=focal_ratio,
                )
            )

        metrics = self._metrics(results, samples)
        reasons.extend(self._hard_rejections(metrics))
        components = self._components(results, samples)
        score = self._score(components)
        if score < self.config["min_score"]:
            reasons.append(f"score {score:.3f} < min_score {self.config['min_score']}")
        metrics["score_components"] = components
        metrics["score"] = score
        unique_reasons = tuple(dict.fromkeys(reasons))
        return PathValidationResult(
            ok=not unique_reasons,
            score=score,
            rejection_reasons=unique_reasons,
            samples=tuple(results),
            metrics=metrics,
        )

    def _status(self, clearance: float | None, in_bounds: bool | None) -> ClearanceStatus:
        if in_bounds is False:
            return ClearanceStatus.OUT_OF_BOUNDS
        if clearance is None:
            return ClearanceStatus.UNKNOWN
        if clearance < self.config["min_clearance_m"]:
            return ClearanceStatus.COLLISION
        if clearance < self.config["near_clearance_m"]:
            return ClearanceStatus.NEAR
        return ClearanceStatus.OK

    def sample_path(self, source) -> list:
        """Sample a :class:`CameraPathDocument` to the validation budget."""
        if hasattr(source, "sample_sequence"):
            total = max(self.config["min_samples"], int(self.config["sample_count"]))
            duration = float(source.duration_sec)
            if total <= 1:
                return [source.sample(0.0)]
            step = duration / (total - 1)
            return [source.sample(min(duration, i * step)) for i in range(total)]
        return list(source)

    def _metrics(self, results: Sequence[SampleResult], samples: Sequence[CameraSample]) -> dict:
        clearances = [r.clearance_m for r in results if r.clearance_m is not None]
        view_scores = [r.view_score for r in results if r.view_score is not None]
        confidences = [s.confidence for s in samples if s.confidence is not None]
        return {
            "sample_count": len(results),
            "max_angular_velocity_deg_sec": max(
                (r.angular_velocity_deg_sec for r in results), default=0.0
            ),
            "max_speed_m_s": max((r.speed_m_s for r in results), default=0.0),
            "max_focal_change_ratio": max((r.focal_change_ratio for r in results), default=0.0),
            "min_clearance_m": min(clearances) if clearances else None,
            "mean_view_score": (sum(view_scores) / len(view_scores)) if view_scores else None,
            "mean_geometry_confidence": (sum(confidences) / len(confidences)) if confidences else None,
            "collision_count": sum(1 for r in results if r.status is ClearanceStatus.COLLISION),
            "out_of_bounds_count": sum(1 for r in results if r.status is ClearanceStatus.OUT_OF_BOUNDS),
            "unknown_clearance_count": sum(1 for r in results if r.status is ClearanceStatus.UNKNOWN),
            "near_limit_count": sum(1 for r in results if r.status is ClearanceStatus.NEAR),
        }

    def _hard_rejections(self, metrics: dict) -> list[str]:
        reasons: list[str] = []
        if self.config["reject_on_collision"] and metrics["collision_count"] > 0:
            reasons.append(
                f"collision_detected ({metrics['collision_count']} samples below "
                f"{self.config['min_clearance_m']}m)"
            )
        if self.config["reject_on_out_of_bounds"] and metrics["out_of_bounds_count"] > 0:
            reasons.append(f"out_of_bounds ({metrics['out_of_bounds_count']} samples)")
        if metrics["max_angular_velocity_deg_sec"] > self.config["max_angular_velocity_deg_sec"]:
            reasons.append(
                f"angular_velocity {metrics['max_angular_velocity_deg_sec']:.2f}deg/s > "
                f"{self.config['max_angular_velocity_deg_sec']}deg/s"
            )
        if metrics["max_speed_m_s"] > self.config["max_speed_m_s"]:
            reasons.append(f"speed {metrics['max_speed_m_s']:.2f}m/s > {self.config['max_speed_m_s']}m/s")
        if metrics["max_focal_change_ratio"] > self.config["max_focal_change_ratio"]:
            reasons.append(
                f"focal_change_ratio {metrics['max_focal_change_ratio']:.3f} > "
                f"{self.config['max_focal_change_ratio']}"
            )
        return reasons

    def _components(self, results: Sequence[SampleResult], samples: Sequence[CameraSample]) -> dict:
        """Per-signal scores in ``[0, 1]`` or ``None`` when evidence is missing."""
        max_angular = max((r.angular_velocity_deg_sec for r in results), default=0.0)
        max_speed = max((r.speed_m_s for r in results), default=0.0)
        angular_score = 1.0 - min(
            1.0, max_angular / max(1e-9, self.config["max_angular_velocity_deg_sec"])
        )
        speed_limit = float(self.config["max_speed_m_s"])
        speed_score = 1.0 if speed_limit <= 0 else 1.0 - min(1.0, max_speed / speed_limit)
        smoothness = (angular_score + speed_score) / 2.0

        known_clearance = [r for r in results if r.clearance_m is not None]
        clearance_score = None
        if known_clearance:
            clearance_score = sum(_clearance_score(r.clearance_m, self.config) for r in known_clearance) / len(
                known_clearance
            )

        view_scores = [r.view_score for r in results if r.view_score is not None]
        visibility = (sum(view_scores) / len(view_scores)) if view_scores else None

        confidences = [s.confidence for s in samples if s.confidence is not None]
        geometry = (sum(confidences) / len(confidences)) if confidences else None

        return {
            "smoothness": max(0.0, min(1.0, smoothness)),
            "clearance": clearance_score,
            "visibility": visibility,
            "geometry": geometry,
        }

    def _score(self, components: dict) -> float:
        """Weighted score over the available components (weights renormalised)."""
        weights = self.config["weights"]
        total_weight = sum(weights[name] for name, value in components.items() if value is not None)
        if total_weight <= 0:
            return 0.0
        score = sum(weights[name] * value for name, value in components.items() if value is not None)
        return max(0.0, min(1.0, score / total_weight))


def _clearance_score(clearance_m: float, config: dict) -> float:
    if clearance_m <= config["min_clearance_m"]:
        return 0.0
    if clearance_m >= config["near_clearance_m"]:
        return 1.0
    span = config["near_clearance_m"] - config["min_clearance_m"]
    return max(0.0, min(1.0, (clearance_m - config["min_clearance_m"]) / span))


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _max_pairwise(points: Sequence[Sequence[float]]) -> float:
    best = 0.0
    items = list(points)
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            best = max(best, _distance(a, b))
    return best


__all__ = [
    "DEFAULT_CONFIG",
    "ClearanceStatus",
    "SceneProxy",
    "CameraSample",
    "SampleResult",
    "PathValidationResult",
    "PointCloudProxy",
    "BoundsProxy",
    "PathValidator",
]
