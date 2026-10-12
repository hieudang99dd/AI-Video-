"""Scene grouping (SKILL_CANONICAL #10 — Pipeline 2).

Groups images into scenes that have a **geometric** relation.  Pairwise
evidence comes from feature matching / geometric verification (COLMAP
``two_view_geometries`` or an equivalent matcher); semantic/global embedding
similarity may only fine-tune an edge that already has geometric evidence —
two different apartments that both contain a "living room" must never be
merged by appearance alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

DEFAULT_CONFIG: dict = {
    "min_match_count": 15,
    "min_inlier_count": 12,
    "min_inlier_ratio": 0.25,
    "min_geometric_confidence": 0.35,
    "min_edge_weight": 0.3,
    "weights": {
        "match_count": 0.2,
        "inlier_ratio": 0.25,
        "homography": 0.2,
        "essential": 0.2,
        "relative_pose": 0.15,
    },
    "match_count_saturation": 200.0,
    "embedding_weight": 0.1,
    "min_images_geometry": 3,
    "min_images_transition": 2,
    "geometry_confidence_threshold": 0.75,
}

UNRESOLVED_MODE = "unresolved"


@dataclass(frozen=True)
class PairRelation:
    """Geometric evidence for one image pair."""

    image_id1: str
    image_id2: str
    match_count: int = 0
    inlier_count: int = 0
    inlier_ratio: float = 0.0
    homography_confidence: float = 0.0
    essential_confidence: float = 0.0
    relative_pose_confidence: float = 0.0
    embedding_similarity: float | None = None

    @property
    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.image_id1, self.image_id2)))  # type: ignore[return-value]

    def to_dict(self) -> dict:
        return {
            "image_id1": self.image_id1,
            "image_id2": self.image_id2,
            "match_count": self.match_count,
            "inlier_count": self.inlier_count,
            "inlier_ratio": round(self.inlier_ratio, 4),
            "homography_confidence": self.homography_confidence,
            "essential_confidence": self.essential_confidence,
            "relative_pose_confidence": self.relative_pose_confidence,
            "embedding_similarity": self.embedding_similarity,
        }


@dataclass(frozen=True)
class SceneGroup:
    """A cluster of images that share verified geometry."""

    id: str
    image_ids: tuple[str, ...]
    confidence: float
    mode: str
    edge_count: int = 0

    @property
    def size(self) -> int:
        return len(self.image_ids)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image_ids": list(self.image_ids),
            "size": self.size,
            "confidence": round(self.confidence, 4),
            "mode": self.mode,
            "edge_count": self.edge_count,
        }


@dataclass(frozen=True)
class SceneGroupingResult:
    """Grouping outcome, including images that could not be attached to a scene."""

    groups: tuple[SceneGroup, ...]
    unresolved: tuple[str, ...]
    edges: tuple[PairRelation, ...]
    diagnostics: dict = field(default_factory=dict)

    def group_for(self, image_id: str) -> SceneGroup | None:
        for group in self.groups:
            if image_id in group.image_ids:
                return group
        return None

    def mode_for(self, image_id: str) -> str:
        group = self.group_for(image_id)
        return group.mode if group else UNRESOLVED_MODE

    def to_dict(self) -> dict:
        return {
            "groups": [g.to_dict() for g in self.groups],
            "unresolved": list(self.unresolved),
            "accepted_edges": [e.to_dict() for e in self.edges],
            "diagnostics": dict(self.diagnostics),
        }


class SceneGrouper:
    """Deterministic geometric graph clustering with union-find."""

    def __init__(self, config: dict | None = None) -> None:
        merged = dict(DEFAULT_CONFIG)
        merged.update(config or {})
        weights = dict(DEFAULT_CONFIG["weights"])
        weights.update((config or {}).get("weights", {}))
        merged["weights"] = weights
        self.config = merged

    def edge_weight(self, relation: PairRelation) -> float:
        """Weight of an edge, or ``0.0`` when geometric evidence is missing."""
        if relation.match_count < self.config["min_match_count"]:
            return 0.0
        if relation.inlier_count < self.config["min_inlier_count"]:
            return 0.0
        if relation.inlier_ratio < self.config["min_inlier_ratio"]:
            return 0.0

        weights = self.config["weights"]
        saturation = float(self.config["match_count_saturation"])
        components = {
            "match_count": min(1.0, relation.match_count / saturation),
            "inlier_ratio": max(0.0, min(1.0, relation.inlier_ratio)),
            "homography": max(0.0, min(1.0, relation.homography_confidence)),
            "essential": max(0.0, min(1.0, relation.essential_confidence)),
            "relative_pose": max(0.0, min(1.0, relation.relative_pose_confidence)),
        }
        total_weight = sum(weights[name] for name in components)
        if total_weight <= 0:
            return 0.0
        geometric = sum(weights[name] * value for name, value in components.items()) / total_weight
        if geometric < self.config["min_geometric_confidence"]:
            return 0.0

        embedding_weight = float(self.config["embedding_weight"])
        if relation.embedding_similarity is not None and embedding_weight > 0.0:
            similarity = max(0.0, min(1.0, relation.embedding_similarity))
            geometric = (1.0 - embedding_weight) * geometric + embedding_weight * similarity
        return max(0.0, min(1.0, geometric))

    def group(self, image_ids: Sequence[str], relations: Iterable[PairRelation]) -> SceneGroupingResult:
        ids = list(dict.fromkeys(image_ids))
        relation_list = list(relations)
        accepted: list[tuple[str, str, float]] = []
        accepted_relations: list[PairRelation] = []
        for relation in relation_list:
            weight = self.edge_weight(relation)
            if weight < self.config["min_edge_weight"]:
                continue
            accepted.append((relation.image_id1, relation.image_id2, weight))
            accepted_relations.append(relation)

        parent = {image_id: image_id for image_id in ids}

        def find(node: str) -> str:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        for image_id1, image_id2, _ in accepted:
            if image_id1 in parent and image_id2 in parent:
                root_a, root_b = find(image_id1), find(image_id2)
                if root_a != root_b:
                    parent[max(root_a, root_b)] = min(root_a, root_b)

        members: dict[str, list[str]] = {}
        for image_id in ids:
            members.setdefault(find(image_id), []).append(image_id)

        edges_by_root: dict[str, list[float]] = {}
        for image_id1, _, weight in accepted:
            if image_id1 in parent:
                edges_by_root.setdefault(find(image_id1), []).append(weight)

        groups: list[SceneGroup] = []
        unresolved: list[str] = []
        for root, group_ids in sorted(members.items()):
            weights = edges_by_root.get(root)
            if not weights:
                unresolved.extend(group_ids)
                continue
            confidence = sum(weights) / len(weights)
            groups.append(
                SceneGroup(
                    id=f"scene-{len(groups) + 1:02d}",
                    image_ids=tuple(sorted(group_ids)),
                    confidence=confidence,
                    mode=self._mode(len(group_ids), confidence),
                    edge_count=len(weights),
                )
            )

        return SceneGroupingResult(
            groups=tuple(groups),
            unresolved=tuple(sorted(unresolved)),
            edges=tuple(accepted_relations),
            diagnostics={
                "image_count": len(ids),
                "relation_count": len(relation_list),
                "accepted_edge_count": len(accepted),
                "rejected_edge_count": len(relation_list) - len(accepted),
                "unresolved_count": len(unresolved),
                "config": {
                    "min_edge_weight": self.config["min_edge_weight"],
                    "min_images_geometry": self.config["min_images_geometry"],
                    "geometry_confidence_threshold": self.config["geometry_confidence_threshold"],
                },
            },
        )

    def _mode(self, size: int, confidence: float) -> str:
        if (
            size >= self.config["min_images_geometry"]
            and confidence >= self.config["geometry_confidence_threshold"]
        ):
            return "geometry"
        if size >= self.config["min_images_transition"]:
            return "transition"
        return "2.5d_lite"

    @staticmethod
    def from_verified_pairs(pairs: Iterable) -> list[PairRelation]:
        """Build relations from :class:`packages.colmap.VerifiedPair` objects."""
        relations: list[PairRelation] = []
        for pair in pairs:
            inlier_ratio = float(getattr(pair, "inlier_ratio", 0.0) or 0.0)
            relations.append(
                PairRelation(
                    image_id1=str(pair.image_id1),
                    image_id2=str(pair.image_id2),
                    match_count=int(getattr(pair, "match_count", 0) or 0),
                    inlier_count=int(getattr(pair, "inlier_count", 0) or 0),
                    inlier_ratio=inlier_ratio,
                    essential_confidence=inlier_ratio,
                    relative_pose_confidence=inlier_ratio,
                )
            )
        return relations


__all__ = [
    "DEFAULT_CONFIG",
    "UNRESOLVED_MODE",
    "PairRelation",
    "SceneGroup",
    "SceneGroupingResult",
    "SceneGrouper",
]
