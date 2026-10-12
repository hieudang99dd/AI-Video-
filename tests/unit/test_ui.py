from fastapi.testclient import TestClient
from app.main import app


def test_ui_root_endpoint():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html = resp.text
    # Verify core standard workflow components are present in UI
    assert "Capability Matrix" in html
    assert "group-scenes" in html or "Gom nhóm Scene" in html
    assert "camera-path" in html or "Biên tập Camera Path" in html
    assert "validate" in html or "Kiểm tra Quỹ đạo" in html
    assert "qc" in html.lower() or "chất lượng" in html.lower()


def test_ui_alias_endpoint():
    client = TestClient(app)
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "AI-Video" in resp.text
