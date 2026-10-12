"""Unit tests for packages.geometry.coords (canonical coordinate transforms)."""

import math

import pytest

from packages.camera_math import normalize_quaternion
from packages.geometry.coords import (
    CANONICAL_UP_AXIS,
    QUATERNION_ORDER,
    UP_AXES,
    VERSION,
    CameraPose,
    canonical_to_colmap,
    canonical_to_nerfstudio,
    colmap_qvec_to_quaternion,
    colmap_to_canonical,
    matrix_to_quaternion,
    nerfstudio_to_canonical,
    points_to_canonical,
    pose_from_colmap,
    pose_to_colmap,
    quaternion_to_colmap_qvec,
    quaternion_to_matrix,
    rotation_angle_deg,
    w2c_to_c2w,
)


def _close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def test_version_and_conventions_are_declared():
    assert VERSION
    assert QUATERNION_ORDER == "xyzw"
    assert CANONICAL_UP_AXIS == "y"
    assert set(UP_AXES) == {"z", "y", "-y"}


def test_quaternion_matrix_round_trip():
    # A non-unit quaternion is normalised on the way in, so compare accordingly.
    q = (0.2, 0.3, 0.4, 0.8386)
    back = matrix_to_quaternion(quaternion_to_matrix(q))
    assert _close(back, normalize_quaternion(q), 1e-9)
    # A unit quaternion round trips exactly.
    unit = (0.0, math.sin(math.pi / 8), 0.0, math.cos(math.pi / 8))
    assert _close(matrix_to_quaternion(quaternion_to_matrix(unit)), unit, 1e-9)


def test_quaternion_to_matrix_identity_is_identity_matrix():
    assert _close([v for row in quaternion_to_matrix((0.0, 0.0, 0.0, 1.0)) for v in row],
                  [v for row in IDENTITY for v in row])


def test_pose_forward_is_camera_z_axis():
    pose = CameraPose.identity((1.0, 2.0, 3.0))
    assert _close(pose.forward(), (0.0, 0.0, 1.0))
    assert _close(pose.position, (1.0, 2.0, 3.0))


def test_pose_rejects_bad_input():
    with pytest.raises(ValueError):
        CameraPose(position=(1.0, 2.0), quaternion=(0.0, 0.0, 0.0, 1.0))
    with pytest.raises(ValueError):
        CameraPose(position=(1.0, 2.0, 3.0), quaternion=(0.0, 0.0, 0.0))


def test_colmap_world_conversion_round_trip_for_every_up_axis():
    pose = CameraPose(position=(1.0, 2.0, 3.0), quaternion=(0.1, 0.2, 0.3, 0.9274))
    for up_axis in UP_AXES:
        back = colmap_to_canonical(canonical_to_colmap(pose, up_axis), up_axis)
        assert _close(back.position, pose.position, 1e-9)
        assert _close(back.quaternion, pose.quaternion, 1e-9)


def test_z_up_maps_colmap_up_axis_onto_canonical_y():
    # A camera 2m above origin along the COLMAP +Z axis must end up +Y (up).
    pose = CameraPose.identity((0.0, 0.0, 2.0))
    converted = colmap_to_canonical(pose, "z")
    assert _close(converted.position, (0.0, 2.0, 0.0), 1e-9)


def test_qvec_tvec_round_trip_via_colmap_pose():
    pose = CameraPose(position=(0.5, 1.5, -2.0), quaternion=(0.0, 0.7071067811865476, 0.0, 0.7071067811865476))
    qvec, tvec = pose_to_colmap(pose, "z")
    back = pose_from_colmap(qvec, tvec, "z")
    assert _close(back.position, pose.position, 1e-9)
    assert _close(back.quaternion, pose.quaternion, 1e-9)


def test_colmap_qvec_is_wxyz_and_matches_xyzw_quaternion():
    xyzw = (0.1, 0.2, 0.3, math.sqrt(1 - 0.01 - 0.04 - 0.09))
    assert quaternion_to_colmap_qvec(xyzw) == (xyzw[3], xyzw[0], xyzw[1], xyzw[2])
    assert _close(colmap_qvec_to_quaternion(quaternion_to_colmap_qvec(xyzw)), xyzw, 1e-12)


def test_w2c_to_c2w_inverts_a_world_to_camera_matrix():
    pose = CameraPose(position=(1.0, 0.0, 0.0), quaternion=(0.0, 0.3826834, 0.0, 0.9238795))
    c2w = pose.to_matrix()
    rotation = [row[:3] for row in c2w[:3]]
    translation = (c2w[0][3], c2w[1][3], c2w[2][3])
    # Inverse rigid transform: R^T for the rotation, -R^T t for the translation.
    rt = tuple(tuple(rotation[j][i] for j in range(3)) for i in range(3))
    offset = tuple(-sum(rt[i][j] * translation[j] for j in range(3)) for i in range(3))
    w2c = tuple(rt[i] + (offset[i],) for i in range(3)) + ((0.0, 0.0, 0.0, 1.0),)

    restored = w2c_to_c2w(w2c)
    for row_expected, row_actual in zip(c2w, restored):
        assert _close(row_expected, row_actual, 1e-9)


def test_nerfstudio_camera_conversion_round_trip():
    pose = CameraPose(position=(0.0, 1.6, 3.0), quaternion=(0.0, 0.0, 0.0, 1.0))
    converted = canonical_to_nerfstudio(pose)
    # nerfstudio/OpenGL cameras look along -Z, so a canonical +Z look flips 180deg.
    assert _close(converted.forward(), (0.0, 0.0, -1.0), 1e-9)
    assert _close(converted.position, pose.position, 1e-9)
    back = nerfstudio_to_canonical(converted)
    assert _close(back.quaternion, pose.quaternion, 1e-9)
    assert _close(back.position, pose.position, 1e-9)


def test_points_to_canonical_matches_pose_conversion():
    pose = CameraPose.identity((0.0, 0.0, 2.0))
    converted = colmap_to_canonical(pose, "z")
    assert points_to_canonical([pose.position], "z") == [converted.position]


def test_rotation_angle_deg_is_zero_for_identical_and_180_for_opposite():
    assert rotation_angle_deg((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)) == pytest.approx(0.0)
    assert rotation_angle_deg((0.0, 0.0, 0.0, 1.0), (1.0, 0.0, 0.0, 0.0)) == pytest.approx(180.0)
    # q and -q describe the same rotation.
    assert rotation_angle_deg((0.0, 0.0, 0.0, -1.0), (0.0, 0.0, 0.0, 1.0)) == pytest.approx(0.0)


def test_pose_from_dict_round_trip():
    pose = CameraPose(position=(1.0, 2.0, 3.0), quaternion=(0.1, 0.2, 0.3, 0.9274))
    assert CameraPose.from_dict(pose.to_dict()) == pose
    assert pose.to_dict()["quaternion_order"] == QUATERNION_ORDER


def test_unsupported_up_axis_is_rejected():
    with pytest.raises(ValueError):
        colmap_to_canonical(CameraPose.identity(), "x")
