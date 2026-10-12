"""Unit tests for packages.path_validation (SKILL_CANONICAL #19-#21, #36).

Covers: invalid path rejection, score bounds, low-confidence fallback and the
clearance/visibility proxies that the geometry backend feeds in.
"""

import pytest

from packages.geometry.camera_path import CameraKeyframeDoc, CameraPathDocument
from packages.path_validation import (
    BoundsProxy,
    CameraSample,
    ClearanceStatus,
    DEFAULT_CONFIG,
    PathValidator,
    PointCloudProxy,
)


IDENTITY = (0.0, 0.0, 0.0, 1.0)
TURN_90 = (0.0, 0.7071067811865476, 0.0, 0.7071067811865476)
TURN_180 = (1.0, 0.0, 0.0, 0.0)


def samples(positions, quaternions=None, times=None, focal=None, confidence=None):
    quaternions = quaternions or [IDENTITY] * len(positions)
    times = times or [float(i) for i in range(len(positions))]
    focal = focal or [32.0] * len(positions)
    return [
        CameraSample(
            timestamp_sec=t,
            position=tuple(p),
            rotation_quaternion=q,
            focal_length_mm=f,
            confidence=confidence,
        )
        for p, q, t, f in zip(positions, quaternions, times, focal)
    ]


def test_default_config_documents_every_gate():
    for key in (
        "min_clearance_m",
        "near_clearance_m",
        "max_angular_velocity_deg_sec",
        "max_focal_change_ratio",
        "min_score",
        "weights",
    ):
        assert key in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["max_angular_velocity_deg_sec"] == 45.0
    assert DEFAULT_CONFIG["min_score"] == 0.65


def test_straight_and_smooth_path_passes_without_a_proxy():
    result = PathValidator().validate(samples([(0, 1.6, 0), (1, 1.6, 0), (2, 1.6, 0)]))
    assert result.ok is True
    assert result.rejection_reasons == ()
    assert 0.0 <= result.score <= 1.0
    assert result.metrics["unknown_clearance_count"] == 3
    assert result.metrics["min_clearance_m"] is None


def test_score_is_always_bounded_between_zero_and_one():
    for config in (None, {"min_score": 0.0}, {"max_angular_velocity_deg_sec": 1.0}):
        result = PathValidator(config).validate(samples([(0, 0, 0), (10, 0, 0), (-10, 5, 3)]))
        assert 0.0 <= result.score <= 1.0


def test_insufficient_samples_is_rejected():
    result = PathValidator().validate(samples([(0, 0, 0)]))
    assert result.ok is False
    assert result.rejection_reasons == ("not_enough_samples",)
    assert result.score == 0.0


def test_excessive_angular_velocity_is_rejected():
    result = PathValidator().validate(
        samples([(0, 0, 0), (0, 0, 0)], quaternions=[IDENTITY, TURN_180], times=[0.0, 0.1])
    )
    assert result.ok is False
    assert any("angular_velocity" in reason for reason in result.rejection_reasons)
    assert result.metrics["max_angular_velocity_deg_sec"] == pytest.approx(1800.0)


def test_rotation_within_the_limit_is_accepted():
    result = PathValidator().validate(
        samples([(0, 0, 0), (0, 0, 0)], quaternions=[IDENTITY, TURN_90], times=[0.0, 3.0])
    )
    assert not any("angular_velocity" in reason for reason in result.rejection_reasons)


def test_excessive_speed_is_rejected():
    result = PathValidator().validate(samples([(0, 0, 0), (40, 0, 0)], times=[0.0, 1.0]))
    assert result.ok is False
    assert any("speed" in reason for reason in result.rejection_reasons)


def test_excessive_focal_change_is_rejected():
    result = PathValidator().validate(
        samples([(0, 0, 0), (1, 0, 0), (2, 0, 0)], focal=[24.0, 32.0, 60.0])
    )
    assert result.ok is False
    assert any("focal_change_ratio" in reason for reason in result.rejection_reasons)


def test_non_monotonic_time_is_rejected():
    result = PathValidator().validate(samples([(0, 0, 0), (1, 0, 0)], times=[1.0, 0.5]))
    assert result.ok is False
    assert "non_monotonic_time" in result.rejection_reasons


def test_score_below_threshold_is_rejected_even_when_no_hard_rule_fires():
    result = PathValidator({"min_score": 1.01}).validate(samples([(0, 0, 0), (1, 0, 0)]))
    assert result.ok is False
    assert any("min_score" in reason for reason in result.rejection_reasons)


def test_collision_with_the_geometry_proxy_is_rejected():
    proxy = PointCloudProxy.from_sampled_cloud(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)], [(0.0, 1.0, 0.0), (1.0, 1.0, 0.0)]
    )
    result = PathValidator().validate(samples([(0.0, 0.02, 0.0), (1.0, 1.0, 0.0)]), proxy)
    assert result.ok is False
    assert any("collision_detected" in reason for reason in result.rejection_reasons)
    assert result.metrics["collision_count"] >= 1
    assert ClearanceStatus.COLLISION in {s.status for s in result.samples}


def test_clear_path_with_a_proxy_passes_and_reports_metrics():
    proxy = PointCloudProxy.from_sampled_cloud(
        [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
        [(0.0, 1.0, 0.0), (1.0, 1.0, 0.0), (2.0, 1.0, 0.0)],
    )
    result = PathValidator().validate(
        samples([(0.0, 1.0, 0.0), (1.0, 1.0, 0.0), (2.0, 1.0, 0.0)]), proxy
    )
    assert result.ok is True, result.rejection_reasons
    assert result.metrics["min_clearance_m"] >= 1.0
    assert result.metrics["unknown_clearance_count"] == 0
    assert 0.0 <= result.metrics["mean_view_score"] <= 1.0


def test_collision_rejection_can_be_disabled_by_config():
    proxy = PointCloudProxy.from_sampled_cloud([(0.0, 0.0, 0.0)], [(0.0, 1.0, 0.0)])
    result = PathValidator({"reject_on_collision": False}).validate(
        samples([(0.0, 0.0, 0.0), (0.5, 0.5, 0.5)]), proxy
    )
    assert not any("collision_detected" in reason for reason in result.rejection_reasons)


def test_out_of_bounds_is_rejected():
    proxy = BoundsProxy(bounds=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)))
    result = PathValidator().validate(samples([(0.0, 0.0, 0.0), (50.0, 0.0, 0.0)]), proxy)
    assert result.ok is False
    assert any("out_of_bounds" in reason for reason in result.rejection_reasons)
    assert any(s.status is ClearanceStatus.OUT_OF_BOUNDS for s in result.samples)


def test_bounds_proxy_accepts_points_on_the_boundary():
    proxy = BoundsProxy(bounds=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)))
    assert proxy.in_bounds((-1.0, 1.0, 0.0)) is True
    assert proxy.in_bounds((1.01, 0.0, 0.0)) is False
    assert BoundsProxy().in_bounds((0.0, 0.0, 0.0)) is None


def test_near_clearance_is_marked_but_not_a_collision():
    proxy = PointCloudProxy.from_sampled_cloud(
        [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0)], [(0.0, 1.0, 0.0), (4.0, 1.0, 0.0)]
    )
    result = PathValidator().validate(
        samples([(0.0, 0.4, 0.0), (4.0, 0.4, 0.0)]), proxy
    )
    assert result.metrics["near_limit_count"] >= 1
    statuses = {s.status for s in result.samples}
    assert ClearanceStatus.NEAR in statuses
    assert ClearanceStatus.COLLISION not in statuses


def test_view_confidence_decays_away_from_training_views():
    proxy = PointCloudProxy.from_sampled_cloud(
        [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)], [(0.0, 1.0, 0.0), (10.0, 1.0, 0.0)]
    )
    near = proxy.view_confidence((0.0, 1.0, 0.0))
    far = proxy.view_confidence((5.0, 1.0, 0.0))
    assert near == pytest.approx(1.0)
    assert 0.0 <= far < near


def test_clearance_and_visibility_are_unknown_without_evidence():
    assert BoundsProxy().query_clearance((0.0, 0.0, 0.0)) is None
    assert BoundsProxy().view_confidence((0.0, 0.0, 0.0)) is None
    assert PointCloudProxy().query_clearance((0.0, 0.0, 0.0)) is None


def test_low_confidence_samples_lower_the_geometry_component():
    config = {"min_score": 0.0}
    confident = PathValidator(config).validate(
        samples([(0, 0, 0), (1, 0, 0)], confidence=0.95)
    )
    doubtful = PathValidator(config).validate(
        samples([(0, 0, 0), (1, 0, 0)], confidence=0.1)
    )
    assert confident.score > doubtful.score
    assert doubtful.metrics["mean_geometry_confidence"] == pytest.approx(0.1)


def test_camera_sample_adapts_a_camera_path_document():
    document = CameraPathDocument(
        keyframes=[
            CameraKeyframeDoc(position=(0.0, 1.6, 0.0), rotation_quaternion=IDENTITY, timestamp_sec=0.0, confidence=0.8),
            CameraKeyframeDoc(position=(2.0, 1.6, 0.0), rotation_quaternion=IDENTITY, timestamp_sec=5.0, confidence=0.8),
        ],
        duration_sec=5.0,
        fps=30,
        width=1280,
        height=720,
    )
    validator = PathValidator({"sample_count": 12})
    sampled = validator.sample_path(document)
    assert len(sampled) == 12
    result = validator.validate(sampled, None)
    assert result.ok is True, result.rejection_reasons
    assert result.samples[0].timestamp_sec == 0.0
    assert result.samples[-1].timestamp_sec == pytest.approx(5.0)
    assert result.metrics["mean_geometry_confidence"] == pytest.approx(0.8)
    assert result.metrics["max_speed_m_s"] < DEFAULT_CONFIG["max_speed_m_s"]


def test_validation_result_serialises_to_json_friendly_dict():
    payload = PathValidator().validate(samples([(0, 0, 0), (1, 0, 0)])).to_dict()
    assert set(payload) == {"ok", "score", "rejection_reasons", "metrics", "samples"}
    assert isinstance(payload["score"], float)
    assert payload["samples"][0]["status"] in {status.value for status in ClearanceStatus}