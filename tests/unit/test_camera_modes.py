from app.services.camera_modes import (
    CameraModeType,
    get_camera_modes_catalog,
    validate_camera_motion,
)


def test_camera_modes_catalog_declares_three_modes():
    catalog = get_camera_modes_catalog()
    assert len(catalog) == 3
    mode_names = {item["mode"] for item in catalog}
    assert mode_names == {
        CameraModeType.IMAGE_2D.value,
        CameraModeType.SCENE_3D.value,
        CameraModeType.AI_VIDEO.value,
    }


def test_2d_image_camera_validation_enforces_safe_zoom_limit():
    # Valid safe zoom
    ok, reasons = validate_camera_motion(
        CameraModeType.IMAGE_2D.value,
        {"start_scale": 1.0, "end_scale": 1.15, "pan_velocity": 0.1},
    )
    assert ok is True
    assert reasons == []

    # Excessive zoom that distorts technical engineering drawings
    bad_ok, bad_reasons = validate_camera_motion(
        CameraModeType.IMAGE_2D.value,
        {"start_scale": 1.0, "end_scale": 1.50, "pan_velocity": 0.1},
    )
    assert bad_ok is False
    assert any("giới hạn an toàn" in r for r in bad_reasons)


def test_3d_scene_camera_reports_fallback_when_cuda_absent():
    catalog = {item["mode"]: item for item in get_camera_modes_catalog()}
    scene_3d = catalog[CameraModeType.SCENE_3D.value]
    assert scene_3d["is_3d_geometry"] is True
    assert scene_3d["preserves_technical_geometry"] is True
    assert scene_3d["fallback_mode"] == CameraModeType.IMAGE_2D.value


def test_ai_video_camera_declared_as_not_preserving_technical_geometry():
    catalog = {item["mode"]: item for item in get_camera_modes_catalog()}
    ai_mode = catalog[CameraModeType.AI_VIDEO.value]
    assert ai_mode["preserves_technical_geometry"] is False
    assert ai_mode["is_3d_geometry"] is False
