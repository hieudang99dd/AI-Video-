"""P01 truthfulness regression tests: no fake AI success, scores or oversized uploads."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.ai_adapter import Wan22Adapter
from app.services.ai_qc import evaluate_ai_enhancement_qc
from app.services.capabilities import get_capabilities
from app.services.storage import LocalStorage


def make_image() -> bytes:
    img = Image.new("RGB", (80, 64), (80, 120, 160))
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


def test_no_qc_inputs_returns_inconclusive_not_fabricated():
    report = evaluate_ai_enhancement_qc([], [])
    assert report["status"] == "INCONCLUSIVE"
    assert report["qc_passed"] is False
    assert report["edge_iou_score"] is None
    assert report["recommendation"] == "do_not_accept"


def test_unmatched_frames_returns_inconclusive(tmp_path: Path):
    frame = tmp_path / "f.png"
    frame.write_bytes(make_image())
    report = evaluate_ai_enhancement_qc([frame, frame], [frame])
    assert report["status"] == "INCONCLUSIVE"
    assert not report["qc_passed"]


def test_wan_adapter_fails_closed_and_creates_no_file(tmp_path: Path):
    source = tmp_path / "source.mp4"
    destination = tmp_path / "ai.mp4"
    source.write_bytes(b"pretend MP4 content")
    with pytest.raises(NotImplementedError, match="not been integrated"):
        Wan22Adapter().enhance_render(source, destination, "road flyover", seed=12)
    assert not destination.exists()


def test_gpu_flag_cannot_make_stub_ready(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "wan_enabled", True)
    monkeypatch.setattr(settings, "moverse_enabled", True)
    flags = get_capabilities()["ai_modules"]
    assert flags["wan2_2"]["available"] is False
    assert flags["moverse"]["available"] is False


def test_storage_rejects_oversize_atomically(tmp_path: Path):
    store = LocalStorage(tmp_path)
    with pytest.raises(ValueError, match="UPLOAD_TOO_LARGE"):
        store.save_stream("project/large.png", io.BytesIO(make_image()), max_bytes=8)
    assert not (tmp_path / "project" / "large.png").exists()
    assert not list(tmp_path.rglob(".upload-*"))


def test_storage_rejects_file_type_mismatch(tmp_path: Path):
    store = LocalStorage(tmp_path)
    with pytest.raises(ValueError, match="IMAGE_FORMAT_MISMATCH"):
        store.save_stream("bad.jpg", io.BytesIO(make_image()), verify_image=True)
    assert not (tmp_path / "bad.jpg").exists()


def test_storage_accepts_valid_png(tmp_path: Path):
    store = LocalStorage(tmp_path)
    uri, digest = store.save_stream("ok.png", io.BytesIO(make_image()), max_bytes=10_000, verify_image=True)
    assert uri == "local://ok.png"
    assert len(digest) == 64
    assert store.resolve(uri).is_file()


def test_ai_endpoint_never_marks_missing_render_complete():
    client = TestClient(app)
    project = client.post("/api/v1/projects", json={"name": "truthfulness-regression"}).json()
    shot = client.post(
        f"/api/v1/projects/{project['id']}/shots",
        json={"asset_ids": ["unavailable-source"], "name": "No output"},
    )
    # Depending on shot asset validation, both 4xx outcomes must never be success.
    if shot.status_code < 400:
        shot_id = shot.json()["id"]
        response = client.post(f"/api/v1/shots/{shot_id}/ai-enhance", json={"module_name": "wan2_2"})
        assert response.status_code == 422
        approve = client.post(f"/api/v1/shots/{shot_id}/ai-qc/decision", json={"decision": "accepted"})
        assert approve.status_code == 409
