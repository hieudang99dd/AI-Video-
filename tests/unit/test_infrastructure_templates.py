from app.services.infrastructure_templates import (
    INFRASTRUCTURE_TEMPLATES,
    generate_infrastructure_storyboard,
    get_infrastructure_templates,
    get_template_by_id,
)


def test_infrastructure_templates_has_all_eight_standard_scenes():
    templates = get_infrastructure_templates()
    assert len(templates) == 8
    expected_ids = {
        "project_overview",
        "alignment_plan",
        "profile_view",
        "cross_sections",
        "bridges_interchanges",
        "drainage_system",
        "traffic_safety",
        "project_outro",
    }
    actual_ids = {t["id"] for t in templates}
    assert actual_ids == expected_ids


def test_get_template_by_id():
    t = get_template_by_id("alignment_plan")
    assert t is not None
    assert "Bình đồ" in t["name"]
    assert t["recommended_camera_mode"] == "2D_IMAGE_CAMERA"

    none_t = get_template_by_id("non_existent_template")
    assert none_t is None


def test_generate_infrastructure_storyboard_with_single_asset():
    storyboard = generate_infrastructure_storyboard("Cao Tốc Bắc Nam", ["asset-uuid-1"])
    assert len(storyboard) == 8
    for shot in storyboard:
        assert shot["asset_ids"] == ["asset-uuid-1"]
        assert shot["duration_sec"] > 0
        assert shot["camera_mode"] in {"2D_IMAGE_CAMERA", "3D_SCENE_CAMERA"}
    assert "CAO TỐC BẮC NAM" in storyboard[0]["overlay_title"]


def test_generate_infrastructure_storyboard_distributes_multiple_assets():
    assets = [f"asset-{i}" for i in range(12)]
    storyboard = generate_infrastructure_storyboard("Dự Án Cầu Vượt", assets)
    assert len(storyboard) == 8
    # Checks that assets are distributed cyclically
    assert storyboard[0]["asset_ids"] == ["asset-0"]
    assert storyboard[1]["asset_ids"] == ["asset-1"]
    assert storyboard[7]["asset_ids"] == ["asset-7"]

