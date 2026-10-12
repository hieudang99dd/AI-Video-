"""Unit tests for packages.colmap.repository (COLMAP text model + database reading)."""

import math
import sqlite3

import pytest

from packages.colmap.repository import (
    DEFAULT_SCENE_CONFIG,
    ColmapCamera,
    ColmapPoint3D,
    ColmapRepository,
    ColmapSceneData,
    VerifiedPair,
)
from packages.geometry.coords import CameraPose, rotation_angle_deg

CAMERAS_TXT = """# Camera list with one line of data per camera:
#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
1 SIMPLE_RADIAL 1920 1080 1800.0 960.0 540.0 -0.01
2 PINHOLE 1920 1080 1800.0 1800.0 960.0 540.0
3 SIMPLE_PINHOLE 1280 720 1000.0 640.0 360.0
"""

IMAGES_TXT = """# Image list with two lines of data per image:
#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
1 0.9 0.0 0.1 0.0 0.1 1.5 2.0 1 img_001.jpg
100.0 200.0 1 120.0 220.0 2 140.0 240.0 -1

2 0.8 0.0 0.2 0.1 0.5 1.6 2.5 2 img_002.jpg
150.0 260.0 1 170.0 280.0 3

3 0.7 0.0 0.3 0.2 0.9 1.7 3.0 3 img_003.jpg
180.0 300.0 2
"""

POINTS3D_TXT = """# 3D point list with one line of data per point:
#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)
1 0.1 0.2 0.3 255 0 0 0.5 1 0 2 0
2 0.4 0.5 0.6 0 255 0 1.0 1 1
3 0.7 0.8 0.9 0 0 255 1.5 2 0
"""


@pytest.fixture
def model(tmp_path):
    """A COLMAP workdir: <tmp>/sparse/0/*.txt (+ database.db when requested)."""
    sparse = tmp_path / "sparse" / "0"
    sparse.mkdir(parents=True)
    (sparse / "cameras.txt").write_text(CAMERAS_TXT, encoding="utf-8")
    (sparse / "images.txt").write_text(IMAGES_TXT, encoding="utf-8")
    (sparse / "points3D.txt").write_text(POINTS3D_TXT, encoding="utf-8")
    return sparse


def write_database(path, pair_rows, match_rows):
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("CREATE TABLE two_view_geometries (pair_id INTEGER, rows INTEGER)")
        connection.execute("CREATE TABLE matches (pair_id INTEGER, rows INTEGER)")
        connection.executemany("INSERT INTO two_view_geometries VALUES (?, ?)", pair_rows)
        connection.executemany("INSERT INTO matches VALUES (?, ?)", match_rows)
    connection.close()


def encode_pair(image_id1: int, image_id2: int) -> int:
    return image_id1 * 2147483647 + image_id2


def test_parse_cameras_supports_common_models(model):
    cameras = ColmapRepository.parse_cameras(model / "cameras.txt")
    assert set(cameras) == {1, 2, 3}
    assert cameras[1].model == "SIMPLE_RADIAL"
    assert cameras[1].intrinsics() == pytest.approx((1800.0, 1800.0, 960.0, 540.0))
    assert cameras[2].intrinsics() == pytest.approx((1800.0, 1800.0, 960.0, 540.0))
    assert cameras[3].intrinsics() == pytest.approx((1000.0, 1000.0, 640.0, 360.0))
    assert cameras[2].focal_length_mm() == pytest.approx(1800.0 / 1920.0 * 36.0)


def test_unsupported_camera_model_raises_actionable_error():
    camera = ColmapCamera(id=1, model="FISHEYE_WEIRD", width=100, height=100, params=(1.0, 2.0))
    with pytest.raises(ValueError, match="unsupported COLMAP camera model"):
        camera.intrinsics()


def test_parse_images_reads_two_lines_per_image(model):
    images = ColmapRepository.parse_images(model / "images.txt")
    assert set(images) == {1, 2, 3}
    assert images[1].name == "img_001.jpg"
    assert images[1].camera_id == 1
    assert images[2].camera_id == 2
    # 3 points2D, of which 2 have a valid point3D id.
    assert images[1].num_points2d == 3
    assert images[1].num_points3d == 2
    assert images[2].num_points2d == 2
    assert images[2].num_points3d == 2
    assert images[1].qvec == pytest.approx((0.9, 0.0, 0.1, 0.0))
    assert images[1].tvec == pytest.approx((0.1, 1.5, 2.0))


def test_parse_images_maps_names_with_spaces_in_file_name(tmp_path):
    sparse = tmp_path / "sparse" / "0"
    sparse.mkdir(parents=True)
    (sparse / "images.txt").write_text(
        "1 1.0 0.0 0.0 0.0 0.0 0.0 0.0 1 my photo 01.jpg\n10.0 20.0 -1\n",
        encoding="utf-8",
    )
    images = ColmapRepository.parse_images(sparse / "images.txt")
    assert images[1].name == "my photo 01.jpg"


def test_parse_points3d_reads_error_and_track(model):
    points = ColmapRepository.parse_points3d(model / "points3D.txt")
    assert set(points) == {1, 2, 3}
    assert points[1].error == pytest.approx(0.5)
    assert points[1].image_ids == (1, 2)
    assert points[2].rgb == (0, 255, 0)


def test_load_reports_statistics_and_diagnostics(model):
    scene = ColmapRepository(model, expected_image_count=3).load()
    assert scene.registered_image_count == 3
    assert scene.registered_ratio == pytest.approx(1.0)
    assert scene.mean_reprojection_error == pytest.approx(1.0)
    assert scene.mean_track_length == pytest.approx(4.0 / 3.0)
    assert scene.scene_extent() > 0.0
    assert scene.diagnostics["database"] is None
    assert "verified_pairs" in scene.diagnostics


def test_registered_views_carry_canonical_poses_and_intrinsics(model):
    scene = ColmapRepository(model, expected_image_count=3).load()
    views = scene.registered_views()
    assert len(views) == 3
    view = next(v for v in views if v.image_id == "1")
    assert isinstance(CameraPose(position=view.position, quaternion=view.quaternion), CameraPose)
    assert view.focal_length_mm == pytest.approx(1800.0 / 1920.0 * 36.0)
    assert 0.0 <= view.confidence <= 1.0


def test_canonical_points_use_the_same_frame_as_camera_centres(model):
    scene = ColmapRepository(model, expected_image_count=3).load()
    points = scene.canonical_points()
    assert len(points) == 3
    # COLMAP +Z is up; canonical Y is up, so the points keep their magnitudes.
    for point, raw in zip(points, scene.points3d.values()):
        assert math.dist(point, (0.0, 0.0, 0.0)) == pytest.approx(math.dist(raw.xyz, (0.0, 0.0, 0.0)))
    assert scene.canonical_points(limit=2)[:1] == points[:1]


def test_quality_gate_rejects_a_scene_with_too_few_cameras(tmp_path):
    sparse = tmp_path / "sparse" / "0"
    sparse.mkdir(parents=True)
    (sparse / "images.txt").write_text(
        "1 1.0 0.0 0.0 0.0 0.0 0.0 0.0 1 a.jpg\n1.0 2.0 -1\n", encoding="utf-8"
    )
    scene = ColmapRepository(sparse, expected_image_count=1).load()
    passed, reasons = scene.quality_gate({"geometry_confidence_threshold": 0.0, "min_registered_ratio": 0.0})
    assert passed is False
    assert any("cameras registered" in reason for reason in reasons)


def test_quality_gate_rejects_low_registered_ratio(model):
    scene = ColmapRepository(model, expected_image_count=10).load()
    assert scene.registered_ratio == pytest.approx(0.3)
    passed, reasons = scene.quality_gate({"geometry_confidence_threshold": 0.0})
    assert passed is False
    assert any("registered ratio" in reason for reason in reasons)


def test_quality_gate_rejects_high_reprojection_error(model):
    scene = ColmapRepository(model, expected_image_count=3).load()
    passed, reasons = scene.quality_gate(
        {"geometry_confidence_threshold": 0.0, "max_mean_reprojection_error": 0.25}
    )
    assert passed is False
    assert any("reprojection error" in reason for reason in reasons)


def test_quality_gate_passes_for_a_healthy_scene_when_thresholds_are_met(model):
    scene = ColmapRepository(model, expected_image_count=3).load()
    passed, reasons = scene.quality_gate(
        {"geometry_confidence_threshold": 0.0, "max_mean_reprojection_error": 2.0}
    )
    assert passed is True, reasons
    assert reasons == []


def test_geometry_confidence_is_bounded_and_increases_with_better_evidence(model):
    good = ColmapRepository(model, expected_image_count=3).load()
    bad = ColmapRepository(model, expected_image_count=30).load()
    assert 0.0 <= bad.geometry_confidence() < good.geometry_confidence() <= 1.0


def test_scene_to_dict_is_json_friendly(model):
    payload = ColmapRepository(model, expected_image_count=3).load().to_dict()
    assert payload["registered_image_count"] == 3
    assert payload["point_count"] == 3
    assert payload["quality_gate"]["passed"] in (True, False)
    assert isinstance(payload["mean_reprojection_error"], float)


def test_verified_pairs_are_read_from_the_colmap_database(model):
    write_database(
        model.parent.parent / "database.db",
        [(encode_pair(1, 2), 140), (encode_pair(2, 3), 90), (encode_pair(1, 3), 0)],
        [(encode_pair(1, 2), 200), (encode_pair(2, 3), 150), (encode_pair(1, 3), 5)],
    )
    scene = ColmapRepository(model, expected_image_count=3).load()
    pairs = scene.verified_pairs
    assert [p.image_id1 for p in pairs] == [1, 2]  # sorted by inlier count, zero dropped
    assert pairs[0].image_id2 == 2
    assert pairs[0].inlier_count == 140
    assert pairs[0].match_count == 200
    assert pairs[0].inlier_ratio == pytest.approx(0.7)
    assert scene.diagnostics["database"].endswith("database.db")


def test_read_verified_pairs_raises_clearly_without_the_table(tmp_path):
    connection = sqlite3.connect(tmp_path / "database.db")
    connection.execute("CREATE TABLE images (image_id INTEGER)")
    connection.commit(); connection.close()
    with pytest.raises(RuntimeError, match="two_view_geometries"):
        ColmapRepository.read_verified_pairs(tmp_path / "database.db")


def test_missing_text_model_raises_actionable_error(tmp_path):
    sparse = tmp_path / "sparse" / "0"
    sparse.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="no COLMAP text model"):
        ColmapRepository(sparse).load()


def test_binary_only_model_tells_the_user_to_convert(tmp_path):
    sparse = tmp_path / "sparse" / "0"
    sparse.mkdir(parents=True)
    (sparse / "images.bin").write_bytes(b"binary")
    with pytest.raises(RuntimeError, match="model_converter"):
        ColmapRepository(sparse).load()


def test_default_scene_config_holds_calibratable_thresholds():
    assert 0.0 < DEFAULT_SCENE_CONFIG["min_registered_ratio"] <= 1.0
    assert DEFAULT_SCENE_CONFIG["geometry_confidence_threshold"] > 0.0
    assert DEFAULT_SCENE_CONFIG["max_mean_reprojection_error"] > 0.0


def test_verified_pair_serialisation():
    pair = VerifiedPair(image_id1=1, image_id2=2, inlier_count=80, match_count=100)
    assert pair.inlier_ratio == pytest.approx(0.8)
    assert pair.to_dict()["inlier_ratio"] == pytest.approx(0.8)
    assert VerifiedPair(1, 2, 5, 0).inlier_ratio == 0.0