"""Keyframe extraction from a reconstructed scene.

Phase 0 vertical slice (SKILL_CANONICAL #0.1) needs **2-3 camera keyframes**
derived from registered images, never invented:

    images -> reconstruction -> keyframes -> safe camera path -> preview -> MP4

Selection policy
    * drop views below ``min_confidence`` when enough better views remain;
    * pick well-spread views with farthest-point sampling;
    * order the picked views as a smooth proximity chain so the path does not
      ping-pong between opposite sides of the scene;
    * report ``insufficient_baseline`` when the chosen views are too close
      together for a trustworthy geometry path (the caller then falls back
      instead of faking motion).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from .camera_path import (
    DEFAULT_FOCAL_LENGTH_MM,
    DEFAULT_SENSOR_WIDTH_MM,
    CameraKeyframeDoc,
    CameraPathDocument,
    CameraPathError,
)

DEFAULT_CONFIG: dict = {
    "max_keyframes": 3,
    "min_keyframes": 2,
    "min_confidence": 0.5,
    "min_baseline_ratio": 0.15,
    "min_view_distance_ratio": 0.05,
}


@dataclass(frozen=True)
class RegisteredView:
    """A reconstructed (registered) image and its canonical camera pose."""

    image_id: str
    name: str
    position: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]
    confidence: float = 1.0
    focal_length_mm: float = DEFAULT_FOCAL_LENGTH_MM
    sensor_width_mm: float = DEFAULT_SENSOR_WIDTH_MM

    def to_keyframe(self, timestamp_sec: float) -> CameraKeyframeDoc:
        return CameraKeyframeDoc(
            position=self.position,
            rotation_quaternion=self.quaternion,
            timestamp_sec=timestamp_sec,
            focal_length_mm=self.focal_length_mm,
            sensor_width_mm=self.sensor_width_mm,
            confidence=self.confidence,
            image_id=self.image_id,
            id=f"kf-{self.image_id}",
        )

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "name": self.name,
            "position": list(self.position),
            "quaternion": list(self.quaternion),
            "quaternion_order": "xyzw",
            "confidence": self.confidence,
            "focal_length_mm": self.focal_length_mm,
            "sensor_width_mm": self.sensor_width_mm,
        }


@dataclass(frozen=True)
class KeyframeSelection:
    """Result of keyframe selection, with the reason for degraded selections."""

    keyframes: tuple[RegisteredView, ...]
    baseline: float
    scene_extent: float
    reason: str | None = None
    diagnostics: dict = field(default_factory=dict)

    @property
    def confidence(self) -> float:
        if not self.keyframes:
            return 0.0
        return sum(v.confidence for v in self.keyframes) / len(self.keyframes)

    def to_camera_path(
        self,
        duration_sec: float,
        fps: int = 30,
        width: int = 1920,
        height: int = 1080,
        easing: str = "cinematic",
        path_type: str = "catmull_rom",
        tension: float = 0.5,
    ) -> CameraPathDocument:
        """Build a :class:`CameraPathDocument` with evenly spaced timestamps."""
        if len(self.keyframes) < 2:
            raise CameraPathError(
                "geometry camera path needs at least 2 registered keyframes; "
                "fall back to 2.5D/transition instead"
            )
        last = duration_sec
        step = last / (len(self.keyframes) - 1)
        docs = [_restamp(view.to_keyframe(i * step), i * step) for i, view in enumerate(self.keyframes)]
        return CameraPathDocument(
            keyframes=docs,
            duration_sec=duration_sec,
            fps=fps,
            width=width,
            height=height,
            easing=easing,
            path_type=path_type,
            tension=tension,
            metadata={
                "keyframe_source": "colmap_registered_views",
                "baseline": round(self.baseline, 4),
                "scene_extent": round(self.scene_extent, 4),
                "selection_reason": self.reason,
                "mean_confidence": round(self.confidence, 4),
            },
        )

    def to_dict(self) -> dict:
        return {
            "keyframe_ids": [v.image_id for v in self.keyframes],
            "baseline": self.baseline,
            "scene_extent": self.scene_extent,
            "reason": self.reason,
            "confidence": self.confidence,
            "diagnostics": dict(self.diagnostics),
        }


def _restamp(doc: CameraKeyframeDoc, timestamp_sec: float) -> CameraKeyframeDoc:
    """Return ``doc`` re-stamped at ``timestamp_sec`` (keeps the dataclass immutable)."""
    return CameraKeyframeDoc(
        position=doc.position,
        rotation_quaternion=doc.rotation_quaternion,
        timestamp_sec=timestamp_sec,
        focal_length_mm=doc.focal_length_mm,
        sensor_width_mm=doc.sensor_width_mm,
        confidence=doc.confidence,
        locked=doc.locked,
        image_id=doc.image_id,
        id=doc.id,
    )


class KeyframeSelector:
    """Deterministic keyframe selection from registered camera views."""

    def __init__(self, config: dict | None = None) -> None:
        merged = dict(DEFAULT_CONFIG)
        merged.update(config or {})
        self.config = merged

    def select(self, views: Sequence[RegisteredView]) -> KeyframeSelection:
        accepted = [v for v in views if v.confidence >= self.config["min_confidence"]]
        reason: str | None = None
        if len(accepted) < 2:
            accepted = list(views)
            reason = "low_confidence_views"
        if not accepted:
            return KeyframeSelection(
                keyframes=(), baseline=0.0, scene_extent=0.0, reason="no_registered_views"
            )

        extent = _max_pairwise_distance(accepted)
        ordered = _order_by_proximity(self._pick(accepted))
        baseline = _max_pairwise_distance(ordered)
        diagnostics = {
            "candidate_count": len(views),
            "accepted_count": len(accepted),
            "chosen_count": len(ordered),
            "scene_extent": round(extent, 4),
            "baseline": round(baseline, 4),
        }
        if len(ordered) < self.config["min_keyframes"]:
            reason = reason or "insufficient_registered_views"
        elif extent > 0 and baseline < self.config["min_baseline_ratio"] * extent:
            reason = reason or "insufficient_baseline"
        return KeyframeSelection(
            keyframes=tuple(ordered),
            baseline=baseline,
            scene_extent=extent,
            reason=reason,
            diagnostics=diagnostics,
        )

    def _pick(self, views: list[RegisteredView]) -> list[RegisteredView]:
        """Farthest-point sampling seeded by the most confident view."""
        limit = int(self.config["max_keyframes"])
        if len(views) <= limit:
            return list(views)
        remaining = list(views)
        seed = max(remaining, key=lambda v: v.confidence)
        chosen = [seed]
        remaining.remove(seed)
        while remaining and len(chosen) < limit:
            best = max(remaining, key=lambda v: min(_distance(v.position, c.position) for c in chosen))
            chosen.append(best)
            remaining.remove(best)
        return chosen


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _max_pairwise_distance(views: Sequence[RegisteredView]) -> float:
    best = 0.0
    for i, a in enumerate(views):
        for b in list(views)[i + 1:]:
            best = max(best, _distance(a.position, b.position))
    return best


def _order_by_proximity(views: Sequence[RegisteredView]) -> list[RegisteredView]:
    """Greedy nearest-neighbour chain starting from one extreme view."""
    if len(views) <= 2:
        return list(views)
    remaining = list(views)
    start = remaining[0]
    best_span = -1.0
    for candidate in remaining:
        span = max(_distance(candidate.position, other.position) for other in remaining)
        if span > best_span:
            best_span = span
            start = candidate
    chain = [start]
    remaining.remove(start)
    while remaining:
        nxt = min(remaining, key=lambda v: _distance(v.position, chain[-1].position))
        chain.append(nxt)
        remaining.remove(nxt)
    return chain


__all__ = [
    "DEFAULT_CONFIG",
    "RegisteredView",
    "KeyframeSelection",
    "KeyframeSelector",
]
