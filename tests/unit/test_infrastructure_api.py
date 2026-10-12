import io
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.db.session import Base, SessionLocal, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def create_sample_image_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (640, 480), (100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def test_api_infrastructure_templates():
    response = client.get("/api/v1/templates/infrastructure")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 8
    assert data[0]["id"] == "project_overview"


def test_api_camera_modes():
    response = client.get("/api/v1/camera-modes")
    assert response.status_code == 200
    modes = {m["mode"]: m for m in response.json()}
    assert "2D_IMAGE_CAMERA" in modes
    assert "3D_SCENE_CAMERA" in modes
    assert "AI_VIDEO_CAMERA" in modes
    assert modes["2D_IMAGE_CAMERA"]["preserves_technical_geometry"] is True


def test_api_ai_adapter_status():
    response = client.get("/api/v1/ai-adapter/status")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False


def test_api_apply_infrastructure_template_creates_storyboard():
    # 1. Create project
    proj_resp = client.post("/api/v1/projects", json={"name": "Cao Tốc Long Thành"})
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    # 2. Upload asset
    img_bytes = create_sample_image_bytes()
    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/assets",
        files={"file": ("infra_overview.jpg", img_bytes, "image/jpeg")},
    )
    assert upload_resp.status_code == 200
    asset_id = upload_resp.json()["id"]

    # 3. Apply infrastructure template
    apply_resp = client.post(
        f"/api/v1/projects/{proj_id}/apply-template",
        json={"template_id": "infrastructure_8_shots"},
    )
    assert apply_resp.status_code == 200
    shots = apply_resp.json()
    assert len(shots) == 8
    assert shots[0]["template_id"] == "project_overview"
    assert "CAO TỐC LONG THÀNH" in shots[0]["overlay_title"]
    assert shots[0]["asset_ids"] == [asset_id]
    assert shots[0]["camera_mode"] == "2D_IMAGE_CAMERA"

    # 4. Trigger timeline render
    timeline_resp = client.post(
        f"/api/v1/projects/{proj_id}/render-timeline",
        json={"resolution": "720p", "fps": 30, "include_subtitles": True, "include_audio": True},
    )
    assert timeline_resp.status_code == 200
    job = timeline_resp.json()
    assert job["type"] == "timeline"
    assert job["status"] == "queued"
    assert job["provenance"]["shot_count"] == 8
