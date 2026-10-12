from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.models.entities import ImageAsset, Project, Shot

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_project_and_shot():
    db = SessionLocal()
    try:
        project = Project(name="Camera Path Test Project")
        db.add(project)
        db.flush()

        asset = ImageAsset(
            project_id=project.id,
            filename="img1.jpg",
            storage_uri="local://test/img1.jpg",
            sha256="abc123456",
        )
        db.add(asset)
        db.flush()

        shot = Shot(
            project_id=project.id,
            name="Test Shot 01",
            asset_ids=[asset.id],
            duration_sec=4.0,
            fps=30,
        )
        db.add(shot)
        db.commit()
        db.refresh(shot)
        return project.id, shot.id
    finally:
        db.close()


def test_get_default_camera_path(test_project_and_shot):
    project_id, shot_id = test_project_and_shot
    resp = client.get(f"/api/v1/shots/{shot_id}/camera-path")
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == 1
    assert data["duration_sec"] == 4.0
    assert data["fps"] == 30
    assert len(data["keyframes"]) == 2
    assert data["keyframes"][0]["timestamp_sec"] == 0.0
    assert data["keyframes"][1]["timestamp_sec"] == 4.0


def test_put_camera_path_valid(test_project_and_shot):
    project_id, shot_id = test_project_and_shot
    payload = {
        "schema_version": 1,
        "duration_sec": 5.0,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "easing": "cinematic",
        "path_type": "catmull_rom",
        "tension": 0.5,
        "keyframes": [
            {
                "id": "k1",
                "position": [0.0, 0.0, 0.0],
                "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
                "quaternion_order": "xyzw",
                "timestamp_sec": 0.0,
                "focal_length_mm": 35.0,
                "sensor_width_mm": 36.0,
                "confidence": 1.0,
                "locked": False,
            },
            {
                "id": "k2",
                "position": [1.0, 0.5, 2.0],
                "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
                "quaternion_order": "xyzw",
                "timestamp_sec": 2.5,
                "focal_length_mm": 35.0,
                "sensor_width_mm": 36.0,
                "confidence": 1.0,
                "locked": False,
            },
            {
                "id": "k3",
                "position": [2.0, 1.0, 4.0],
                "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
                "quaternion_order": "xyzw",
                "timestamp_sec": 5.0,
                "focal_length_mm": 35.0,
                "sensor_width_mm": 36.0,
                "confidence": 1.0,
                "locked": False,
            },
        ],
        "metadata": {"user_edited": True},
    }

    put_resp = client.put(f"/api/v1/shots/{shot_id}/camera-path", json=payload)
    assert put_resp.status_code == 200
    res = put_resp.json()
    assert len(res["keyframes"]) == 3
    assert res["duration_sec"] == 5.0

    # Verify GET returns updated data
    get_resp = client.get(f"/api/v1/shots/{shot_id}/camera-path")
    assert get_resp.status_code == 200
    assert get_resp.json()["metadata"]["user_edited"] is True


def test_put_camera_path_rejects_invalid_timestamps(test_project_and_shot):
    project_id, shot_id = test_project_and_shot
    invalid_payload = {
        "schema_version": 1,
        "duration_sec": 5.0,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "easing": "cinematic",
        "path_type": "catmull_rom",
        "tension": 0.5,
        "keyframes": [
            {
                "position": [0.0, 0.0, 0.0],
                "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
                "timestamp_sec": 3.0,
            },
            {
                "position": [1.0, 0.0, 1.0],
                "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
                "timestamp_sec": 1.0,  # Non-monotonic!
            },
        ],
    }

    resp = client.put(f"/api/v1/shots/{shot_id}/camera-path", json=invalid_payload)
    assert resp.status_code == 400
    assert "strictly increasing" in resp.json()["detail"]


def test_validate_camera_path_endpoint(test_project_and_shot):
    project_id, shot_id = test_project_and_shot
    payload = {
        "schema_version": 1,
        "duration_sec": 4.0,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "easing": "cinematic",
        "path_type": "catmull_rom",
        "tension": 0.5,
        "keyframes": [
            {
                "position": [0.0, 0.0, 0.0],
                "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
                "timestamp_sec": 0.0,
            },
            {
                "position": [0.0, 0.0, 2.0],
                "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
                "timestamp_sec": 4.0,
            },
        ],
    }

    resp = client.post(f"/api/v1/shots/{shot_id}/camera-path/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["score"] > 0.0
    assert len(data["rejection_reasons"]) == 0
