"""Unit tests for packages.geometry.keyframes (2-3 keyframes from registered views)."""

import pytest

from packages.geometry.camera_path import CameraPathError
from packages.geometry.keyframes import (
    DEFAULT_CONFIG,
    KeyframeSelection,
    KeyframeSelector,
    RegisteredView,
)


def view(index: int, x: float, confidence: float = 0.9, y: float = 1.6) -> RegisteredView:
    return RegisteredView(
        image_id=str(index),
        name=f"img_{index:03d}.jpg",
        position=(x, y, 0.0),
        quaternion=(0.0, 0.0, 0.0, 1.0),
        confidence=confidence,
    )


def line_of(count: int, spacing: float = 1.0, confidence: float = 0.9) -> list[RegisteredView]:
    return [view(i, i * spacing, confidence) for i in range(count)]


def test_default_config_matches_phase0_budget():
    assert DEFAULT_CONFIG["max_keyframes"] == 3
    assert DEFAULT_CONFIG["min_keyframes"] == 2
    assert 0.0 < DEFAULT_CONFIG["min_confidence"] < 1.0
    assert DEFAULT_CONFIG["min_baseline_ratio"] > 0.0


def test_registered_view_converts_to_keyframe_document():
    doc = view(7, 2.0).to_keyframe(1.25)
    assert doc.timestamp_sec == 1.25
    assert doc.image_id == "7"
    assert doc.id == "kf-7"
    assert doc.position == (2.0, 1.6, 0.0)
    assert doc.confidence == pytest.approx(0.9)
    assert doc.to_dict()["quaternion_order"] == "xyzw"


def test_three_spread_views_are_all_selected_without_degradation():
    selection = KeyframeSelector().select(line_of(3))
    assert selection.reason is None
    assert len(selection.keyframes) == 3
    assert selection.baseline == pytest.approx(2.0)
    assert selection.scene_extent == pytest.approx(2.0)
    assert selection.confidence == pytest.approx(0.9)
    assert selection.diagnostics["candidate_count"] == 3


def test_more_views_than_budget_are_reduced_to_max_keyframes():
    selection = KeyframeSelector().select(line_of(6))
    assert len(selection.keyframes) == DEFAULT_CONFIG["max_keyframes"]
    # Farthest-point sampling must keep the extremes of the camera line.
    xs = sorted(v.position[0] for v in selection.keyframes)
    assert xs[0] == pytest.approx(0.0)
    assert xs[-1] == pytest.approx(5.0)


def test_selected_views_are_ordered_as_a_smooth_chain():
    selection = KeyframeSelector().select(line_of(6))
    xs = [v.position[0] for v in selection.keyframes]
    increasing = all(a < b for a, b in zip(xs, xs[1:]))
    decreasing = all(a > b for a, b in zip(xs, xs[1:]))
    assert increasing or decreasing, xs


def test_farthest_point_sampling_seeds_on_the_most_confident_view():
    # 4 candidates but a budget of 3 forces sampling: the confident view at x=0.2
    # is the seed, then the two farthest views (x=9.0 and x=0.0) follow.
    views = [view(0, 0.0, 0.5), view(1, 0.1, 0.5), view(2, 0.2, 0.99), view(3, 9.0, 0.5)]
    selection = KeyframeSelector().select(views)
    chosen = {v.image_id for v in selection.keyframes}
    assert len(selection.keyframes) == DEFAULT_CONFIG["max_keyframes"]
    assert "2" in chosen  # confidence seed
    assert "3" in chosen and "0" in chosen  # spread kept
    assert "1" not in chosen  # crowded middle dropped
    assert selection.reason is None


def test_low_confidence_views_are_reported():
    selection = KeyframeSelector().select([view(i, float(i), 0.2) for i in range(3)])
    assert selection.reason == "low_confidence_views"
    assert len(selection.keyframes) == 3
    assert selection.diagnostics["accepted_count"] == 3


def test_single_high_confidence_view_leaves_one_candidate():
    selection = KeyframeSelector().select([view(0, 0.0, 0.9)])
    assert selection.diagnostics["accepted_count"] == 1
    assert selection.reason in {"low_confidence_views", "insufficient_registered_views"}


def test_empty_scene_reports_no_registered_views():
    selection = KeyframeSelector().select([])
    assert selection.keyframes == ()
    assert selection.reason == "no_registered_views"
    assert selection.confidence == 0.0


def test_insufficient_baseline_is_detected_when_config_demands_it():
    selector = KeyframeSelector({"min_baseline_ratio": 1.5})
    selection = selector.select(line_of(4))
    assert selection.reason == "insufficient_baseline"


def test_selection_builds_a_valid_camera_path_with_even_timestamps():
    selection = KeyframeSelector().select(line_of(3))
    document = selection.to_camera_path(duration_sec=5.0, fps=30, width=1280, height=720)
    assert document.problems() == []
    assert [k.timestamp_sec for k in document.keyframes] == [0.0, 2.5, 5.0]
    assert document.metadata["keyframe_source"] == "colmap_registered_views"
    assert document.metadata["baseline"] == pytest.approx(2.0)
    assert document.frame_count == 150


def test_camera_path_requires_at_least_two_keyframes():
    selection = KeyframeSelection(keyframes=(view(0, 0.0),), baseline=0.0, scene_extent=0.0)
    with pytest.raises(CameraPathError):
        selection.to_camera_path(duration_sec=5.0)


def test_selection_serialisation_is_json_friendly():
    payload = KeyframeSelector().select(line_of(3)).to_dict()
    assert payload["keyframe_ids"] == ["0", "1", "2"]
    assert payload["reason"] is None
    assert payload["baseline"] == pytest.approx(2.0)
    assert payload["confidence"] == pytest.approx(0.9)