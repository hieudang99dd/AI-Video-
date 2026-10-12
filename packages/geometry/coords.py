"""Canonical coordinate transforms.

This is the **only** place in the repository where coordinate frames are
converted (see ``packages/geometry/__init__.py``).  Do not convert elsewhere.

World frames
    canonical  : right-handed, +X right, +Y up, +Z toward the viewer (Y-up)
    colmap     : right-handed, frame chosen by the SfM initialisation.  The
                 caller declares which axis is up through ``up_axis``
                 ("z" default, "y", "-y")
    nerfstudio : right-handed, +Y up, +Z toward the viewer (same as canonical)

Camera frames
    canonical (OpenCV style)  : +X right, +Y down, +Z forward
    nerfstudio (OpenGL style) : +X right, +Y up,   +Z backward (looks along -Z)

A :class:`CameraPose` stores the camera centre in the world frame plus a
quaternion ordered ``(x, y, z, w)`` that rotates camera-frame vectors into
world-frame vectors (camera-to-world).  COLMAP ``qvec``/``tvec`` are
world-to-camera and ``qvec`` is ordered ``(w, x, y, z)`` — always go through the
helpers in this module instead of converting ad hoc.

Any change to a convention must bump :data:`VERSION` and update
``tests/unit/test_geometry_coords.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Sequence

from packages.camera_math import normalize_quaternion

VERSION = "1.0.0"

QUATERNION_ORDER = "xyzw"
"""Quaternion component order used by packages/geometry and packages/camera_math."""

COLMAP_QUATERNION_ORDER = "wxyz"
"""Component order used by COLMAP ``qvec`` (and COLMAP text models)."""

CANONICAL_UP_AXIS = "y"
"""Axis that points up in the canonical world frame."""

UP_AXES = ("z", "y", "-y")

Matrix3 = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
Matrix4 = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]
Quaternion = tuple[float, float, float, float]


@dataclass(frozen=True)
class CameraPose:
    """Camera centre in a world frame plus a camera-to-world quaternion."""

    position: tuple[float, float, float]
    quaternion: Quaternion

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", _vec3(self.position))
        object.__setattr__(self, "quaternion", normalize_quaternion(self.quaternion))

    @classmethod
    def identity(cls, position: Sequence[float] = (0.0, 0.0, 0.0)) -> "CameraPose":
        """Pose at ``position`` looking along the canonical camera +Z axis."""
        return cls(position=_vec3(position), quaternion=(0.0, 0.0, 0.0, 1.0))

    @classmethod
    def from_matrix(cls, matrix: Sequence[Sequence[float]]) -> "CameraPose":
        """Build a pose from a 4x4 (or 3x4) camera-to-world matrix."""
        rows = [list(map(float, row)) for row in matrix]
        if len(rows) < 3 or any(len(row) < 4 for row in rows[:3]):
            raise ValueError("camera-to-world matrix must be at least 3x4")
        return cls(
            position=(rows[0][3], rows[1][3], rows[2][3]),
            quaternion=matrix_to_quaternion(_mat3(rows[:3])),
        )

    def with_position(self, position: Sequence[float]) -> "CameraPose":
        return replace(self, position=_vec3(position))

    def rotation_matrix(self) -> Matrix3:
        """Camera-to-world rotation (columns are the camera axes in world space)."""
        return quaternion_to_matrix(self.quaternion)

    def camera_axes(self) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
        """World-space directions of the camera X/Y/Z axes."""
        return _columns(self.rotation_matrix())

    def forward(self) -> tuple[float, float, float]:
        """World-space view direction (canonical camera +Z)."""
        return self.camera_axes()[2]

    def to_matrix(self) -> Matrix4:
        """4x4 camera-to-world matrix (row-major) usable by NumPy/nerfstudio."""
        rotation = self.rotation_matrix()
        p = self.position
        return (
            (rotation[0][0], rotation[0][1], rotation[0][2], p[0]),
            (rotation[1][0], rotation[1][1], rotation[1][2], p[1]),
            (rotation[2][0], rotation[2][1], rotation[2][2], p[2]),
            (0.0, 0.0, 0.0, 1.0),
        )

    def to_dict(self) -> dict:
        return {
            "position": list(self.position),
            "quaternion": list(self.quaternion),
            "quaternion_order": QUATERNION_ORDER,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CameraPose":
        return cls(position=tuple(data["position"]), quaternion=tuple(data["quaternion"]))


# --------------------------------------------------------------------------- #
# camera-to-world <-> world-to-camera
# --------------------------------------------------------------------------- #
def w2c_to_c2w(matrix: Sequence[Sequence[float]]) -> Matrix4:
    """Invert a world-to-camera matrix into a camera-to-world matrix."""
    rotation = _mat3([row[:3] for row in matrix[:3]])
    t = (float(matrix[0][3]), float(matrix[1][3]), float(matrix[2][3]))
    rt = _transpose3(rotation)
    position = _mat_vec(rt, (-t[0], -t[1], -t[2]))
    return (
        (rt[0][0], rt[0][1], rt[0][2], position[0]),
        (rt[1][0], rt[1][1], rt[1][2], position[1]),
        (rt[2][0], rt[2][1], rt[2][2], position[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


def c2w_to_w2c(matrix: Sequence[Sequence[float]]) -> Matrix4:
    """Invert a camera-to-world matrix into a world-to-camera matrix."""
    return w2c_to_c2w(matrix)


def pose_matrix_from_qvec_tvec(qvec: Sequence[float], tvec: Sequence[float]) -> Matrix4:
    """Compose a COLMAP world-to-camera matrix from ``qvec`` ``(w, x, y, z)`` and ``tvec``."""
    rotation = quaternion_to_matrix(colmap_qvec_to_quaternion(qvec))
    t = _vec3(tvec)
    return (
        (rotation[0][0], rotation[0][1], rotation[0][2], t[0]),
        (rotation[1][0], rotation[1][1], rotation[1][2], t[1]),
        (rotation[2][0], rotation[2][1], rotation[2][2], t[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


def colmap_qvec_to_quaternion(qvec: Sequence[float]) -> Quaternion:
    """Convert a COLMAP ``qvec`` ``(w, x, y, z)`` to ``(x, y, z, w)``."""
    w, x, y, z = _vec4(qvec)
    return normalize_quaternion((x, y, z, w))


def quaternion_to_colmap_qvec(quaternion: Sequence[float]) -> tuple[float, float, float, float]:
    """Convert a ``(x, y, z, w)`` quaternion to COLMAP ``qvec`` ``(w, x, y, z)``."""
    x, y, z, w = normalize_quaternion(quaternion)
    return (w, x, y, z)


# --------------------------------------------------------------------------- #
# world frame conversions
# --------------------------------------------------------------------------- #
def _world_matrix(up_axis: str) -> Matrix3:
    """Rotation mapping a declared world frame onto the canonical Y-up frame."""
    key = up_axis.strip().lower()
    if key == "y":
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    if key == "z":
        # colmap +X -> +X, +Y -> -Z, +Z -> +Y
        return ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
    if key == "-y":
        # colmap +X -> +X, +Y -> -Y, +Z -> -Z
        return ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
    raise ValueError(f"unsupported up_axis {up_axis!r}; expected one of {UP_AXES}")


def colmap_to_canonical(pose: CameraPose, up_axis: str = "z") -> CameraPose:
    """Convert a pose expressed in the COLMAP world frame to the canonical frame.

    ``pose.quaternion`` must already rotate camera-frame vectors into the COLMAP
    world frame — use :func:`pose_from_colmap` for raw ``qvec``/``tvec`` input.
    """
    m = _world_matrix(up_axis)
    rotation = _mat_mul(m, pose.rotation_matrix())
    return CameraPose(position=_mat_vec(m, pose.position), quaternion=matrix_to_quaternion(rotation))


def canonical_to_colmap(pose: CameraPose, up_axis: str = "z") -> CameraPose:
    """Inverse of :func:`colmap_to_canonical`."""
    m = _transpose3(_world_matrix(up_axis))
    rotation = _mat_mul(m, pose.rotation_matrix())
    return CameraPose(position=_mat_vec(m, pose.position), quaternion=matrix_to_quaternion(rotation))


def points_to_canonical(points: Sequence[Sequence[float]], up_axis: str = "z") -> list[tuple[float, float, float]]:
    """Map world-space points (e.g. a COLMAP sparse cloud) into the canonical frame."""
    m = _world_matrix(up_axis)
    return [_mat_vec(m, point) for point in points]


def pose_from_colmap(qvec: Sequence[float], tvec: Sequence[float], up_axis: str = "z") -> CameraPose:
    """Build a canonical pose from a raw COLMAP world-to-camera ``qvec``/``tvec``."""
    camera_to_world = w2c_to_c2w(pose_matrix_from_qvec_tvec(qvec, tvec))
    return colmap_to_canonical(CameraPose.from_matrix(camera_to_world), up_axis=up_axis)


def pose_to_colmap(pose: CameraPose, up_axis: str = "z"):
    """Return ``(qvec, tvec)`` in COLMAP order for a canonical pose."""
    colmap_pose = canonical_to_colmap(pose, up_axis=up_axis)
    w2c = c2w_to_w2c(colmap_pose.to_matrix())
    rotation = _mat3([row[:3] for row in w2c[:3]])
    q = matrix_to_quaternion(rotation)
    return quaternion_to_colmap_qvec(q), (w2c[0][3], w2c[1][3], w2c[2][3])


# --------------------------------------------------------------------------- #
# nerfstudio (OpenGL camera axes) conversions
# --------------------------------------------------------------------------- #
_CAMERA_AXIS_FLIP: Matrix3 = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))


def canonical_to_nerfstudio(pose: CameraPose) -> CameraPose:
    """Convert a canonical pose (OpenCV camera axes) to nerfstudio/OpenGL camera axes."""
    rotation = _mat_mul(pose.rotation_matrix(), _CAMERA_AXIS_FLIP)
    return CameraPose(position=pose.position, quaternion=matrix_to_quaternion(rotation))


def nerfstudio_to_canonical(pose: CameraPose) -> CameraPose:
    """Inverse of :func:`canonical_to_nerfstudio`."""
    rotation = _mat_mul(pose.rotation_matrix(), _CAMERA_AXIS_FLIP)
    return CameraPose(position=pose.position, quaternion=matrix_to_quaternion(rotation))


# --------------------------------------------------------------------------- #
# quaternion / matrix helpers (local so the package stays dependency-free)
# --------------------------------------------------------------------------- #
def quaternion_to_matrix(quaternion: Sequence[float]) -> Matrix3:
    """Rotation matrix for a quaternion ordered ``(x, y, z, w)``."""
    x, y, z, w = normalize_quaternion(quaternion)
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return (
        (1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy)),
        (2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx)),
        (2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy)),
    )


def matrix_to_quaternion(matrix: Sequence[Sequence[float]]) -> Quaternion:
    """Quaternion ``(x, y, z, w)`` for a 3x3 rotation matrix."""
    m = _mat3(matrix)
    m00, m01, m02 = m[0]
    m10, m11, m12 = m[1]
    m20, m21, m22 = m[2]
    trace = m00 + m11 + m22
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m21 - m12) / s
        y = (m02 - m20) / s
        z = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        w = (m21 - m12) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        w = (m02 - m20) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        w = (m10 - m01) / s
        x = (m02 + m20) / s
        y = (m12 + m21) / s
        z = 0.25 * s
    return normalize_quaternion((x, y, z, w))


def rotation_angle_deg(a: Sequence[float], b: Sequence[float]) -> float:
    """Smallest rotation angle in degrees between two quaternions."""
    qa = normalize_quaternion(a)
    qb = normalize_quaternion(b)
    dot = abs(sum(x * y for x, y in zip(qa, qb)))
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(2.0 * math.acos(dot))


def vec3(values: Sequence[float]) -> tuple[float, float, float]:
    """Validate and coerce a 3-component vector."""
    return _vec3(values)


def _vec3(values: Sequence[float]) -> tuple[float, float, float]:
    out = tuple(float(v) for v in values)
    if len(out) != 3:
        raise ValueError("vector must have 3 components")
    return out  # type: ignore[return-value]


def _vec4(values: Sequence[float]) -> tuple[float, float, float, float]:
    out = tuple(float(v) for v in values)
    if len(out) != 4:
        raise ValueError("quaternion must have 4 components")
    return out  # type: ignore[return-value]


def _mat3(rows: Sequence[Sequence[float]]) -> Matrix3:
    out = tuple(tuple(float(v) for v in list(row)[:3]) for row in list(rows)[:3])
    if len(out) != 3 or any(len(row) != 3 for row in out):
        raise ValueError("matrix must be 3x3")
    return out  # type: ignore[return-value]


def _mat_mul(a: Matrix3, b: Matrix3) -> Matrix3:
    return tuple(  # type: ignore[return-value]
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3)
    )


def _mat_vec(m: Matrix3, v: Sequence[float]) -> tuple[float, float, float]:
    x, y, z = _vec3(v)
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z,
        m[1][0] * x + m[1][1] * y + m[1][2] * z,
        m[2][0] * x + m[2][1] * y + m[2][2] * z,
    )


def _transpose3(m: Matrix3) -> Matrix3:
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def _columns(m: Matrix3) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (m[0][0], m[1][0], m[2][0]),
        (m[0][1], m[1][1], m[2][1]),
        (m[0][2], m[1][2], m[2][2]),
    )


__all__ = [
    "VERSION",
    "QUATERNION_ORDER",
    "COLMAP_QUATERNION_ORDER",
    "CANONICAL_UP_AXIS",
    "UP_AXES",
    "Matrix3",
    "Matrix4",
    "Quaternion",
    "CameraPose",
    "colmap_to_canonical",
    "canonical_to_colmap",
    "canonical_to_nerfstudio",
    "nerfstudio_to_canonical",
    "pose_from_colmap",
    "pose_to_colmap",
    "points_to_canonical",
    "pose_matrix_from_qvec_tvec",
    "colmap_qvec_to_quaternion",
    "quaternion_to_colmap_qvec",
    "quaternion_to_matrix",
    "matrix_to_quaternion",
    "rotation_angle_deg",
    "vec3",
    "w2c_to_c2w",
    "c2w_to_w2c",
]
