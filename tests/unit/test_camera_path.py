"""Unit tests for packages.geometry.camera_path (schema, sampling, ns export)."""

import math

import pytest

from packages.geometry.camera_path import (
    CameraKeyframeDoc,
    CameraPathDocument,
    CameraPathError,
    DEFAULT_FOCAL_LENGTH_MM,
    DEFAULT_SENSOR_WIDTH_MM,
    EASINGS,
    PATH_TYPES,
    SCHEMA_VERSION,
)
from packages.geometry.coords import CameraPose, rotation_angle_deg


def make_document(**overrides) -> CameraPathDocument:
    default = dict(
        keyframes=[
            CameraKeyframeDoc(position=(0.0, 1.6, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=0.0),
            CameraKeyframeDoc(position=(2.0, 1.6, 0.0), rotation_quaternion=(0.0, 0.2, 0.0, 0.98), timestamp_sec=2.5),
            CameraKeyframeDoc(position=(4.0, 1.6, 0.0), rotation_quaternion=(0.0, 0.4, 0.0, 0.92), timestamp_sec=5.0),
        ],
        duration_sec=5.0,
        fps=30,
        width=1280,
        height=720,
    )
    default.update(overrides)
    return CameraPathDocument(**default)


def test_constants_are_versioned():
    assert SCHEMA_VERSION == 1
    assert "cinematic" in EASINGS
    assert "catmull_rom" in PATH_TYPES
    assert DEFAULT_FOCAL_LENGTH_MM > 0 and DEFAULT_SENSOR_WIDTH_MM > 0


def test_valid_document_has_no_problems():
    document = make_document()
    assert document.problems() == []
    assert document.validate() is document


def test_frame_count_matches_duration_and_fps():
    assert make_document().frame_count == 150
    assert make_document(duration_sec=0.5, fps=12).frame_count == 6


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"keyframes": []}, "at least 2 keyframes"),
        ({"duration_sec": 0.0}, "duration_sec must be positive"),
        ({"fps": 5}, "fps must be between"),
        ({"fps": 120}, "fps must be between"),
        ({"width": 0}, "width and height must be positive"),
        ({"easing": "wobble"}, "easing must be one of"),
        ({"path_type": "spiral"}, "path_type must be one of"),
        ({"tension": 2.0}, "tension must be within"),
        ({"schema_version": 99}, "schema_version"),
    ],
)
def test_invalid_document_fields_are_reported(overrides, expected):
    document = make_document(**overrides)
    problems = document.problems()
    assert any(expected in problem for problem in problems), problems
    with pytest.raises(CameraPathError):
        document.validate()


def test_non_increasing_timestamps_are_rejected():
    document = make_document(
        keyframes=[
            CameraKeyframeDoc(position=(0.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=0.0),
            CameraKeyframeDoc(position=(1.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=0.0),
        ],
        duration_sec=2.0,
    )
    assert any("strictly increasing" in problem for problem in document.problems())


def test_keyframe_beyond_duration_is_rejected():
    document = make_document(
        keyframes=[
            CameraKeyframeDoc(position=(0.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=0.0),
            CameraKeyframeDoc(position=(1.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=9.0),
        ],
        duration_sec=5.0,
    )
    assert any("exceeds duration_sec" in problem for problem in document.problems())


def test_sampling_hits_keyframe_endpoints():
    document = make_document()
    start = document.sample(0.0)
    end = document.sample(document.duration_sec)
    assert start.position == pytest.approx(document.keyframes[0].position)
    assert end.position == pytest.approx(document.keyframes[-1].position)
    assert rotation_angle_deg(start.rotation_quaternion, document.keyframes[0].rotation_quaternion) < 1e-6
    assert rotation_angle_deg(end.rotation_quaternion, document.keyframes[-1].rotation_quaternion) < 1e-6


def test_sampling_is_clamped_outside_the_timeline():
    document = make_document()
    assert document.sample(-5.0).timestamp_sec == 0.0
    assert document.sample(99.0).timestamp_sec == document.duration_sec


def test_sample_sequence_is_monotonic_and_complete():
    document = make_document()
    samples = document.sample_sequence()
    assert len(samples) == document.frame_count
    stamps = [s.timestamp_sec for s in samples]
    assert stamps == sorted(stamps)
    assert stamps[0] == 0.0
    assert stamps[-1] == pytest.approx(document.duration_sec)


def test_rotation_interpolation_is_continuous_slerp():
    document = make_document()
    samples = document.sample_sequence()
    steps = [
        rotation_angle_deg(a.rotation_quaternion, b.rotation_quaternion)
        for a, b in zip(samples, samples[1:])
    ]
    assert max(steps) < 1.0  # degrees per frame: no jump for a ~25deg key rotation
    assert any(step > 0.0 for step in steps)


def test_sampled_quaternions_stay_normalised():
    document = make_document()
    for sample in document.sample_sequence():
        norm = math.sqrt(sum(v * v for v in sample.rotation_quaternion))
        assert norm == pytest.approx(1.0, abs=1e-9)


def test_easing_changes_midpoint_progress():
    linear = make_document(easing="linear").sample(0.5)
    cinematic = make_document(easing="cinematic").sample(0.5)
    assert linear.position[0] != cinematic.position[0]


def test_linear_path_type_is_a_straight_line():
    document = make_document(path_type="linear")
    middle = document.sample(1.25)  # halfway through the first segment in time
    assert 0.0 < middle.position[0] < 2.0


def test_bezier_and_catmull_rom_stay_near_the_keyframes():
    for path_type in ("catmull_rom", "cubic_bezier"):
        document = make_document(path_type=path_type)
        for sample in document.sample_sequence():
            assert -1.0 <= sample.position[0] <= 5.0
            assert 0.5 <= sample.position[1] <= 2.7


def test_focal_length_interpolates_independently():
    document = make_document(
        keyframes=[
            CameraKeyframeDoc(position=(0.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=0.0, focal_length_mm=24.0),
            CameraKeyframeDoc(position=(1.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=5.0, focal_length_mm=48.0),
        ]
    )
    assert document.sample(0.0).focal_length_mm == pytest.approx(24.0)
    assert document.sample(5.0).focal_length_mm == pytest.approx(48.0)
    assert 24.0 < document.sample(2.5).focal_length_mm < 48.0


def test_document_serialisation_round_trip():
    document = make_document(scene_id="scene-1", metadata={"keyframe_source": "colmap_registered_views"})
    restored = CameraPathDocument.from_dict(document.to_dict())
    assert restored.to_dict() == document.to_dict()
    assert restored.scene_id == "scene-1"


def test_nerfstudio_camera_path_uses_vertical_fov_and_gl_convention():
    document = make_document(width=1920, height=1080)
    payload = document.to_nerfstudio_camera_path()
    assert payload["camera_type"] == "PerspectiveCamera"
    assert payload["render_width"] == 1920 and payload["render_height"] == 1080
    assert payload["fps"] == 30 and payload["seconds"] == pytest.approx(5.0)
    assert len(payload["camera_path"]) == document.frame_count
    camera = payload["camera_path"][0]
    assert len(camera["camera_to_world"]) == 16
    assert camera["aspect"] == pytest.approx(1920 / 1080)
    # 32mm on a 36mm sensor at 16:9 => ~35.1deg vertical, well under the 58.7deg horizontal.
    assert camera["fov"] == pytest.approx(35.117, abs=0.01)
    assert camera["fov"] < 58.7
    assert payload["default_fov"] == pytest.approx(camera["fov"])


def test_nerfstudio_transform_matrix_is_row_major_camera_to_world():
    document = make_document(width=1280, height=720)
    values = document.to_nerfstudio_camera_path()["camera_path"][0]["camera_to_world"]
    rows = [values[i * 4:(i + 1) * 4] for i in range(4)]
    assert rows[3] == [0.0, 0.0, 0.0, 1.0]
    assert rows[0][3] == pytest.approx(0.0)
    assert rows[1][3] == pytest.approx(1.6)
    assert rows[2][3] == pytest.approx(0.0)


def test_vertical_fov_returns_a_larger_angle_for_a_taller_frame():
    document = make_document(width=900, height=1600)
    camera = document.to_nerfstudio_camera_path()["camera_path"][0]
    assert camera["fov"] > 35.117


def test_single_keyframe_document_is_rejected():
    document = make_document(
        keyframes=[
            CameraKeyframeDoc(position=(0.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=0.0)
        ]
    )
    with pytest.raises(CameraPathError):
        document.sample(0.0)


def test_bad_focal_length_raises_instead_of_producing_nan():
    document = make_document(
        keyframes=[
            CameraKeyframeDoc(position=(0.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=0.0, focal_length_mm=0.0),
            CameraKeyframeDoc(position=(1.0, 0.0, 0.0), rotation_quaternion=(0.0, 0.0, 0.0, 1.0), timestamp_sec=5.0, focal_length_mm=0.0),
        ]
    )
    assert any("focal/sensor values must be positive" in problem for problem in document.problems())


def test_keyframe_doc_accepts_pose_and_round_trips():
    pose = CameraPose(position=(1.0, 2.0, 3.0), quaternion=(0.0, 0.0, 0.0, 1.0))
    doc = CameraKeyframeDoc.from_pose(pose, 1.5, image_id="42")
    assert doc.to_pose().position == pose.position
    restored = CameraKeyframeDoc.from_dict(doc.to_dict())
    assert restored.to_dict() == doc.to_dict()
    assert restored.to_dict()["quaternion_order"] == "xyzw"