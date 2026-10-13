from __future__ import annotations

from pathlib import Path
import tempfile
from PIL import Image, ImageDraw
import pytest

from app.services.ai_adapter import dust3r_adapter, get_all_ai_modules_status, moverse_adapter, wan22_adapter
from app.services.ai_qc import AI_ENHANCED_DISCLAIMER, evaluate_ai_enhancement_qc
from app.services.blender_engine import export_and_optionally_run_blender_scene, generate_blender_python_script
from app.services.camera_planner import (
    TWINMOTION_PRESETS,
    CameraSourceMode,
    generate_shot_camera_plan,
    get_all_camera_presets,
    resolve_camera_source_mode,
    save_custom_preset,
)
from app.services.capabilities import get_capabilities
from app.services.image_analysis import (
    SEMANTIC_CATEGORIES,
    analyze_image,
    compute_dhash,
    detect_duplicates_and_overlaps,
    estimate_pairwise_overlap,
    hamming_distance,
)
from app.services.job_manager import (
    PipelineState,
    redact_secrets,
    transition_job_state,
    validate_state_transition,
    validate_upload_safety,
)


def _make_test_image(path: Path, size=(800, 450), color=(90, 110, 130), draw_lines: bool = True) -> Path:
    img = Image.new("RGB", size, color)
    if draw_lines:
        draw = ImageDraw.Draw(img)
        draw.line([(0, size[1] // 2), (size[0], size[1] // 2)], fill=(230, 230, 230), width=4)
        draw.rectangle([(120, 100), (360, 300)], outline=(20, 200, 240), width=3)
    img.save(path, quality=92)
    return path


def test_ten_twinmotion_camera_presets_complete():
    required_ids = {
        "establishing_shot",
        "aerial_flyover",
        "follow_road",
        "approach_shot",
        "orbit_shot",
        "intersection_reveal",
        "bridge_pass",
        "culvert_drainage_detail",
        "low_angle_road",
        "closing_shot",
    }
    assert required_ids.issubset(set(TWINMOTION_PRESETS.keys()))
    for pid in required_ids:
        preset = TWINMOTION_PRESETS[pid]
        assert preset.fov_deg > 0
        assert preset.recommended_duration_sec > 0
        assert preset.shake_level == 0.0  # Shake disabled by default per Section 4.4
        assert len(preset.start_offset) == 3
        assert len(preset.end_offset) == 3


def test_custom_camera_preset_save_and_list(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    saved = save_custom_preset(
        {
            "id": "custom_bridge_zoom",
            "name": "Custom Bridge Zoom",
            "base_preset_id": "bridge_pass",
            "fov_deg": 40.0,
            "duration_sec": 8.0,
            "speed": 1.1,
            "shake_level": 0.0,
            "easing": "cinematic",
        }
    )
    assert saved["id"] == "custom_bridge_zoom"
    assert saved["is_custom"] is True
    all_presets = {p["id"]: p for p in get_all_camera_presets()}
    assert "custom_bridge_zoom" in all_presets


def test_three_camera_source_modes_never_conflated():
    # Mode A requested when 3D scene IS reconstructed -> stays Mode A
    mode_a, note_a = resolve_camera_source_mode("A_RECONSTRUCTED_3D", asset_count=4, scene_reconstructed=True)
    assert mode_a == CameraSourceMode.RECONSTRUCTED_3D.value
    assert "A_RECONSTRUCTED_3D" in note_a

    # Mode A requested when 3D scene is NOT reconstructed -> explicit fallback to B or C
    mode_fb_b, note_fb_b = resolve_camera_source_mode("A_RECONSTRUCTED_3D", asset_count=3, scene_reconstructed=False)
    assert mode_fb_b == CameraSourceMode.ORDERED_IMAGE_PATH.value
    assert "Fallback A -> B_ORDERED_IMAGE_PATH" in note_fb_b

    mode_fb_c, note_fb_c = resolve_camera_source_mode("A_RECONSTRUCTED_3D", asset_count=1, scene_reconstructed=False)
    assert mode_fb_c == CameraSourceMode.SINGLE_IMAGE_2_5D.value
    assert "Fallback A -> C_SINGLE_IMAGE_2_5D" in note_fb_c


def test_camera_planner_generates_valid_slerp_trajectory():
    plan = generate_shot_camera_plan(
        preset_id="orbit_shot",
        source_mode="A_RECONSTRUCTED_3D",
        asset_ids=["a1", "a2", "a3"],
        duration_sec=6.0,
        fps=30,
        reconstructed_poses=[
            {"position": [-6.0, -8.0, 5.0], "quaternion": [1.0, 0.0, 0.0, 0.0]},
            {"position": [6.0, -8.0, 5.0], "quaternion": [0.9659, 0.0, 0.2588, 0.0]},
        ],
    )
    assert plan["source_mode"] == "A_RECONSTRUCTED_3D"
    assert len(plan["trajectory"]) >= 8
    assert plan["safety_validation"]["passed"] is True
    assert plan["safety_validation"]["scale_status"] == "uncalibrated"


def test_image_analysis_classification_duplicates_and_overlap(tmp_path):
    img1 = _make_test_image(tmp_path / "cau_vuot_ic01.jpg", color=(100, 110, 120))
    img2 = _make_test_image(tmp_path / "cau_vuot_ic01_copy.jpg", color=(100, 110, 120))
    img3 = _make_test_image(tmp_path / "mat_cat_ngang_km10.jpg", size=(400, 300), color=(240, 240, 240), draw_lines=False)

    m1 = analyze_image(img1)
    m2 = analyze_image(img2)
    m3 = analyze_image(img3)

    assert m1["semantic_category"] == "bridge"
    assert m3["semantic_category"] == "cross_section_detail"
    assert "low_resolution" in m3["quality_warnings"]
    assert "blurry" in m3["quality_warnings"]
    assert hamming_distance(m1["perceptual_hash"], m2["perceptual_hash"]) == 0

    records = [
        {"id": "1", "sha256": "aaa", "perceptual_hash": m1["perceptual_hash"], "path": img1, "quality_warnings": m1["quality_warnings"]},
        {"id": "2", "sha256": "bbb", "perceptual_hash": m2["perceptual_hash"], "path": img2, "quality_warnings": m2["quality_warnings"]},
    ]
    annotated = detect_duplicates_and_overlaps(records)
    assert annotated[1]["is_duplicate"] is True
    assert annotated[1]["duplicate_of"] == "1"
    assert "duplicate_or_near_duplicate" in annotated[1]["quality_warnings"]

    ov = estimate_pairwise_overlap(img1, img2)
    assert 0.5 <= ov <= 1.0


def test_blender_engine_exports_deterministic_script_and_trajectory(tmp_path):
    img = _make_test_image(tmp_path / "road.jpg")
    plan = generate_shot_camera_plan(
        preset_id="follow_road",
        source_mode="C_SINGLE_IMAGE_2_5D",
        asset_ids=["a1"],
        duration_sec=4.0,
    )
    out_mp4 = tmp_path / "out.mp4"
    res = export_and_optionally_run_blender_scene(
        shot_id="shot_01",
        shot_name="Follow Road Shot",
        camera_plan=plan,
        image_paths=[img],
        workdir=tmp_path / "blender_work",
        output_mp4_path=out_mp4,
        execute_if_available=False,
    )
    assert Path(res["blender_script_path"]).exists()
    assert Path(res["camera_trajectory_path"]).exists()
    script_content = Path(res["blender_script_path"]).read_text(encoding="utf-8")
    assert "import bpy" in script_content
    assert "QUATERNION" in script_content
    assert "Scale Status: uncalibrated" in script_content


def test_ai_modules_license_and_qc_guard(tmp_path):
    # DUSt3R must be disabled by default because of CC BY-NC-SA 4.0 non-commercial license
    ok, reason = dust3r_adapter.check_license_and_availability()
    assert ok is False
    assert "CC BY-NC-SA 4.0" in reason

    statuses = get_all_ai_modules_status()
    assert statuses["dust3r"]["commercial_allowed"] is False
    assert statuses["wan2_2"]["license"] == "Apache-2.0"

    # Unit-only pair comparison; this does not prove AI inference occurred
    f1 = _make_test_image(tmp_path / "orig.jpg", draw_lines=True)
    qc_ok = evaluate_ai_enhancement_qc([f1, f1], [f1, f1])
    assert qc_ok["qc_passed"] is True
    assert qc_ok["label"] == "AI_ENHANCED"
    assert AI_ENHANCED_DISCLAIMER in qc_ok["disclaimer"]

    # AI QC should flag geometry distortion when AI frame loses structural edges
    f_blank = _make_test_image(tmp_path / "distorted.jpg", color=(20, 20, 20), draw_lines=False)
    qc_bad = evaluate_ai_enhancement_qc([f1, f1], [f_blank, f_blank])
    assert qc_bad["qc_passed"] is False
    assert qc_bad["recommendation"] == "reject_and_revert_to_3d"
    assert len(qc_bad["warnings"]) >= 1


def test_job_state_machine_and_security_guards():
    assert validate_state_transition(PipelineState.CREATED.value, PipelineState.VALIDATING.value) is True
    assert validate_state_transition(PipelineState.RENDERING.value, PipelineState.COMPOSING.value) is True

    redacted = redact_secrets("Error calling endpoint with api_key=sk-1234567890abcdef and Bearer secret_tok_99")
    assert "sk-1234567890abcdef" not in redacted
    assert "secret_tok_99" not in redacted
    assert "[REDACTED]" in redacted

    safe = validate_upload_safety("C:\\fakepath\\Binh Do Tuyen Km10.png", content_size_bytes=1024, current_project_assets=2)
    assert safe.endswith(".png")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        validate_upload_safety("malware.exe")


def test_capabilities_reports_hardware_and_ffmpeg():
    caps = get_capabilities()
    assert caps["ffmpeg"]["available"] is True
    assert "blender" in caps
    assert "gpu_hardware" in caps
    assert "disk" in caps
    assert "ai_modules" in caps
