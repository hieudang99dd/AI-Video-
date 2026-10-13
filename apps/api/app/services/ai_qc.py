from __future__ import annotations

from pathlib import Path
from typing import Any
from PIL import Image
import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


AI_ENHANCED_DISCLAIMER = (
    "AI_ENHANCED — Hình ảnh đã qua xử lý bởi mô hình AI, chỉ phục vụ minh họa trình chiếu, "
    "không phải hồ sơ thiết kế kỹ thuật gốc (Civil 3D / InfraWorks)."
)


def _compute_edge_mask(gray: np.ndarray) -> np.ndarray:
    if cv2 is not None:
        edges = cv2.Canny(gray.astype(np.uint8), 60, 160)
        return edges > 0
    dx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    dy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    mag = np.hypot(dx, dy)
    thresh = max(15.0, float(np.percentile(mag, 85)))
    return mag >= thresh


def compare_frame_pair(orig_img: Image.Image, ai_img: Image.Image) -> dict[str, float]:
    """Compare a single original 3D/plate frame against an AI-enhanced frame for structural geometry fidelity."""
    g_orig = np.asarray(orig_img.convert("L").resize((320, 180)), dtype=np.float32)
    g_ai = np.asarray(ai_img.convert("L").resize((320, 180)), dtype=np.float32)

    edges_orig = _compute_edge_mask(g_orig)
    edges_ai = _compute_edge_mask(g_ai)

    # Dilate slightly (1px tolerance) so lighting shifts don't penalize intact road/bridge edges
    if cv2 is not None:
        kernel = np.ones((3, 3), dtype=np.uint8)
        e_orig_dil = cv2.dilate(edges_orig.astype(np.uint8), kernel, iterations=1) > 0
        e_ai_dil = cv2.dilate(edges_ai.astype(np.uint8), kernel, iterations=1) > 0
    else:
        e_orig_dil = edges_orig
        e_ai_dil = edges_ai

    inter = float(np.logical_and(e_orig_dil, e_ai_dil).sum())
    union = float(np.logical_or(edges_orig, edges_ai).sum())
    edge_iou = 1.0 if union < 10.0 else min(1.0, inter / max(1.0, union))

    # Normalized structural correlation
    a_norm = g_orig - g_orig.mean()
    b_norm = g_ai - g_ai.mean()
    denom = float(np.linalg.norm(a_norm) * np.linalg.norm(b_norm))
    structural_corr = 1.0 if denom < 1e-5 else max(0.0, min(1.0, float((a_norm * b_norm).sum() / denom)))

    return {
        "edge_iou_score": round(edge_iou, 4),
        "structural_consistency_score": round(structural_corr, 4),
    }


def evaluate_ai_enhancement_qc(
    original_frames: list[Path] | None = None,
    ai_frames: list[Path] | None = None,
    edge_iou_threshold: float = 0.62,
    structural_threshold: float = 0.75,
) -> dict[str, Any]:
    """Evaluate AI-enhanced output against original 3D/plate render to guard against geometry hallucination.

    Detects:
    - Road lane or alignment warping (``road_geometry_drift``)
    - Bridge pier / retaining wall distortion (``bridge_edge_distortion``)
    - Frame-to-frame luminance flicker (``temporal_flicker_detected``)
    """
    if (
        not original_frames
        or not ai_frames
        or len(original_frames) != len(ai_frames)
        or not all(Path(p).is_file() for p in [*original_frames, *ai_frames])
    ):
        return {
            "qc_passed": False,
            "status": "INCONCLUSIVE",
            "edge_iou_score": None,
            "structural_consistency_score": None,
            "temporal_stability_score": None,
            "thresholds": {
                "min_edge_iou": edge_iou_threshold,
                "min_structural_consistency": structural_threshold,
                "min_temporal_stability": 0.78,
            },
            "warnings": ["Missing or unmatched source/enhanced frame pairs; quality was not measured."],
            "recommendation": "do_not_accept",
            "label": "AI_QC_NOT_RUN",
            "disclaimer": AI_ENHANCED_DISCLAIMER,
        }

    pairs = list(zip(original_frames, ai_frames))[:10]
    edge_scores: list[float] = []
    struct_scores: list[float] = []
    lum_means: list[float] = []
    for orig_p, ai_p in pairs:
        with Image.open(orig_p) as oi, Image.open(ai_p) as ai:
            metrics = compare_frame_pair(oi, ai)
            edge_scores.append(metrics["edge_iou_score"])
            struct_scores.append(metrics["structural_consistency_score"])
            lum_means.append(float(np.asarray(ai.convert("L"), dtype=np.float32).mean() / 255.0))
    mean_edge_iou = round(float(np.mean(edge_scores)), 4)
    mean_struct = round(float(np.mean(struct_scores)), 4)
    if len(lum_means) >= 2:
        temporal_stability = round(max(0.0, 1.0 - float(np.abs(np.diff(lum_means)).mean() * 4.0)), 4)
    else:
        temporal_stability = None
    warnings: list[str] = []
    if mean_edge_iou < edge_iou_threshold:
        warnings.append("bridge_edge_distortion: Phát hiện biến dạng cạnh kết cấu công trình (cầu/tường chắn/taluy).")
    if mean_struct < structural_threshold:
        warnings.append("road_geometry_drift: Phát hiện sai lệch hình học tim đường hoặc mặt cắt ngang so với bản render 3D gốc.")
    if temporal_stability is not None and temporal_stability < 0.78:
        warnings.append("temporal_flicker_detected: Phát hiện nhấp nháy ánh sáng (flicker) giữa các frame liên tiếp.")

    qc_passed = len(warnings) == 0 and temporal_stability is not None
    return {
        "qc_passed": qc_passed,
        "status": "PASSED" if qc_passed else ("INCONCLUSIVE" if temporal_stability is None else "FAILED"),
        "edge_iou_score": mean_edge_iou,
        "structural_consistency_score": mean_struct,
        "temporal_stability_score": temporal_stability,
        "thresholds": {
            "min_edge_iou": edge_iou_threshold,
            "min_structural_consistency": structural_threshold,
            "min_temporal_stability": 0.78,
        },
        "warnings": warnings,
        "recommendation": "accept" if qc_passed else ("do_not_accept" if temporal_stability is None else "reject_and_revert_to_3d"),
        "label": "AI_ENHANCED",
        "disclaimer": AI_ENHANCED_DISCLAIMER,
    }
