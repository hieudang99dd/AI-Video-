from __future__ import annotations

import io
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
import pytest

from app.db.session import engine, ensure_sqlite_schema
from app.main import app


@pytest.fixture(autouse=True)
def _init_db():
    ensure_sqlite_schema(engine)


def _create_png_bytes(width: int = 800, height: int = 450, color=(70, 95, 120), label: str = "KM10") -> bytes:
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(40, 40), (width - 40, height - 40)], outline=(14, 165, 233), width=4)
    draw.line([(0, height // 2), (width, height // 2)], fill=(220, 230, 240), width=5)
    draw.text((80, 80), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_e2e_case1_single_image_to_2_5d_mp4():
    """Case 1: 1 Civil 3D / InfraWorks image -> 2.5D camera motion (Mode C) -> real MP4."""
    client = TestClient(app)
    proj = client.post("/api/v1/projects", json={"name": "Case 1 - Single Image 2.5D"}).json()
    pid = proj["id"]

    img_bytes = _create_png_bytes(label="OVERVIEW_IC01")
    asset = client.post(
        f"/api/v1/projects/{pid}/assets",
        files={"file": ("overview_ic01.jpg", img_bytes, "image/jpeg")},
    ).json()

    analysis = client.post(f"/api/v1/projects/{pid}/analyze").json()
    assert analysis["suggested_mode"] == "2.5d_lite"
    assert analysis["assets"][0]["semantic_category"] == "overview"

    shot = client.post(
        f"/api/v1/projects/{pid}/shots",
        json={
            "name": "Shot 01 - Establishing",
            "asset_ids": [asset["id"]],
            "preset": "establishing_shot",
            "source_mode": "C_SINGLE_IMAGE_2_5D",
            "duration_sec": 0.5,
            "fps": 12,
            "overlay_title": "TONG QUAN DU AN",
            "subtitle_text": "Mo phong 2.5D an toan tu 1 anh tinh",
        },
    ).json()
    assert shot["source_mode"] == "C_SINGLE_IMAGE_2_5D"
    assert len(shot["trajectory"]) >= 8

    job = client.post(f"/api/v1/shots/{shot['id']}/preview").json()
    ran = client.post(f"/api/v1/render-jobs/{job['id']}/run-now").json()
    assert ran["status"] == "completed"
    assert ran["state_machine_step"] == "COMPLETED"
    assert ran["output_uri"] is not None

    dl = client.get(f"/api/v1/render-jobs/{job['id']}/download")
    assert dl.status_code == 200
    assert len(dl.content) > 1024


def test_e2e_case2_ordered_images_to_timeline_mp4_with_manifest():
    """Case 2: 3 ordered images -> grouping/ordering -> camera presets -> Blender export -> AI QC -> Timeline MP4 + Manifest."""
    client = TestClient(app)
    proj = client.post("/api/v1/projects", json={"name": "Cao Toc Bac Nam Km10-Km35"}).json()
    pid = proj["id"]

    names = ["overview_km10.jpg", "bridge_pier_km15.jpg", "culvert_drainage_km20.jpg"]
    asset_ids = []
    for idx, fname in enumerate(names):
        b = _create_png_bytes(color=(60 + idx * 25, 90, 130), label=fname)
        a = client.post(
            f"/api/v1/projects/{pid}/assets",
            files={"file": (fname, b, "image/jpeg")},
        ).json()
        asset_ids.append(a["id"])

    # Reorder & assign scene group
    reordered = client.put(
        f"/api/v1/projects/{pid}/assets/order",
        json={"ordered_asset_ids": list(reversed(asset_ids)), "scene_group": "main_corridor"},
    )
    assert reordered.status_code == 200
    assert reordered.json()[0]["id"] == asset_ids[-1]
    assert reordered.json()[0]["scene_group"] == "main_corridor"

    # Override semantic category on first asset
    patched = client.patch(
        f"/api/v1/projects/{pid}/assets/{asset_ids[0]}",
        json={"semantic_category": "intersection"},
    )
    assert patched.status_code == 200
    assert patched.json()["semantic_category"] == "intersection"
    assert patched.json()["user_overridden_category"] is True

    # Analyze project
    client.post(f"/api/v1/projects/{pid}/analyze")

    # Create a multi-image shot using B_ORDERED_IMAGE_PATH
    shot = client.post(
        f"/api/v1/projects/{pid}/shots",
        json={
            "name": "Corridor Flyover",
            "asset_ids": asset_ids,
            "preset": "aerial_flyover",
            "source_mode": "B_ORDERED_IMAGE_PATH",
            "duration_sec": 0.5,
            "fps": 12,
        },
    ).json()
    assert shot["source_mode"] == "B_ORDERED_IMAGE_PATH"

    # Regenerate camera path with orbit_shot preset
    updated_shot = client.post(
        f"/api/v1/shots/{shot['id']}/camera-path/generate",
        json={"preset": "orbit_shot", "source_mode": "B_ORDERED_IMAGE_PATH", "duration_sec": 0.5, "fps": 12},
    ).json()
    assert updated_shot["preset"] == "orbit_shot"

    # Export Blender headless script (.py) and trajectory (.json)
    blender_res = client.post(
        f"/api/v1/shots/{shot['id']}/blender-scene",
        json={"execute_if_available": False, "resolution": "720p"},
    )
    assert blender_res.status_code == 200
    assert Path(blender_res.json()["blender_script_path"]).exists()

    # Optional AI Enhancement + AI QC Reject (revert to 3D/plate original)
    ai_job = client.post(
        f"/api/v1/shots/{shot['id']}/ai-enhance",
        json={"module_name": "wan2_2", "prompt": "Realistic concrete bridge daylight", "seed": 42},
    )
    assert ai_job.status_code == 422  # no completed source render; never fake success
    assert "Render a source clip first" in ai_job.json()["detail"]

    qc_decision = client.post(
        f"/api/v1/shots/{shot['id']}/ai-qc/decision",
        json={"decision": "rejected", "notes": "Keep original engineering geometry"},
    )
    assert qc_decision.status_code == 200
    assert qc_decision.json()["ai_enabled"] is False
    assert qc_decision.json()["ai_status"] == "rejected_reverted_to_3d"

    # Render full timeline with intro & outro cards
    tl_job = client.post(
        f"/api/v1/projects/{pid}/render-timeline",
        json={
            "resolution": "720p",
            "fps": 12,
            "include_subtitles": True,
            "include_audio": False,
            "intro_title": "DU AN CAO TOC BAC NAM",
            "outro_title": "BAN QUYEN TU VAN THIET KE",
        },
    ).json()
    tl_done = client.post(f"/api/v1/render-jobs/{tl_job['id']}/run-now").json()
    assert tl_done["status"] == "completed"
    assert tl_done["provenance"]["intro_applied"] is True
    assert tl_done["provenance"]["outro_applied"] is True

    # Verify Project Manifest JSON (Section 4.9)
    manifest = client.get(f"/api/v1/projects/{pid}/manifest").json()
    assert manifest["project_id"] == pid
    assert manifest["reconstruction"]["scale_status"] == "uncalibrated"
    assert manifest["scene_representation"]["coordinate_system"] == "uncalibrated_local"
    assert manifest["scene_representation"]["unit"] == "relative_units"
    assert len(manifest["images"]) == 3
    assert len(manifest["shots"]) == 1
    assert manifest["final_output"]["mp4_path"] is not None


def test_failure_modes_corrupt_unsupported_and_duplicate_assets():
    """Failure tests (Section 8.3): unsupported file format, corrupt image, duplicate upload."""
    client = TestClient(app)
    proj = client.post("/api/v1/projects", json={"name": "Failure Test Project"}).json()
    pid = proj["id"]

    # 1. Unsupported format (.dwg / .exe) -> HTTP 415
    bad_ext = client.post(
        f"/api/v1/projects/{pid}/assets",
        files={"file": ("drawing.dwg", b"AC1032_CAD_BINARY", "application/octet-stream")},
    )
    assert bad_ext.status_code == 415

    # 2. Corrupt image bytes uploaded with .jpg extension -> graceful error in /analyze
    client.post(
        f"/api/v1/projects/{pid}/assets",
        files={"file": ("corrupt.jpg", b"not_a_valid_jpeg_stream", "image/jpeg")},
    )
    valid_bytes = _create_png_bytes(label="VALID_01")
    client.post(
        f"/api/v1/projects/{pid}/assets",
        files={"file": ("valid_1.jpg", valid_bytes, "image/jpeg")},
    )
    # Upload exact duplicate image
    client.post(
        f"/api/v1/projects/{pid}/assets",
        files={"file": ("valid_1_dup.jpg", valid_bytes, "image/jpeg")},
    )

    analysis = client.post(f"/api/v1/projects/{pid}/analyze")
    assert analysis.status_code == 200
    items = analysis.json()["assets"]
    errors = [x for x in items if "error" in x]
    valid_items = [x for x in items if "error" not in x]
    assert len(errors) == 1
    assert any(x.get("is_duplicate") is True for x in valid_items)
