from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Sequence

from app.services.capabilities import get_capabilities


class CameraModeType(str, Enum):
    IMAGE_2D = "2D_IMAGE_CAMERA"
    SCENE_3D = "3D_SCENE_CAMERA"
    AI_VIDEO = "AI_VIDEO_CAMERA"


@dataclass(frozen=True)
class CameraModeInfo:
    mode: str
    display_name: str
    description: str
    is_3d_geometry: bool
    preserves_technical_geometry: bool
    min_assets: int
    max_safe_zoom: float
    max_pan_velocity: float
    requires_cuda: bool
    fallback_mode: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CAMERA_MODES: dict[str, CameraModeInfo] = {
    CameraModeType.IMAGE_2D.value: CameraModeInfo(
        mode=CameraModeType.IMAGE_2D.value,
        display_name="2D Image Camera (Chuyển động trên ảnh nguồn)",
        description=(
            "Camera 2D tịnh tiến và thu phóng mượt mà trên ảnh bản vẽ/phối cảnh gốc. "
            "Bảo toàn 100% hình học công trình kỹ thuật, không làm biến dạng phối cảnh. "
            "Chạy an toàn trên mọi CPU."
        ),
        is_3d_geometry=False,
        preserves_technical_geometry=True,
        min_assets=1,
        max_safe_zoom=1.35,
        max_pan_velocity=0.25,
        requires_cuda=False,
        fallback_mode=None,
    ),
    CameraModeType.SCENE_3D.value: CameraModeInfo(
        mode=CameraModeType.SCENE_3D.value,
        display_name="3D Scene Camera (Camera không gian 3D thực)",
        description=(
            "Camera tự do di chuyển trong không gian 3D được tái tạo từ SfM (COLMAP) hoặc 3DGS. "
            "Sử dụng nội suy Quaternion SLERP, kiểm soát góc quay và va chạm. "
            "Yêu cầu ảnh chụp có góc nhìn overlap và GPU tương thích."
        ),
        is_3d_geometry=True,
        preserves_technical_geometry=True,
        min_assets=3,
        max_safe_zoom=2.0,
        max_pan_velocity=0.50,
        requires_cuda=True,
        fallback_mode=CameraModeType.IMAGE_2D.value,
    ),
    CameraModeType.AI_VIDEO.value: CameraModeInfo(
        mode=CameraModeType.AI_VIDEO.value,
        display_name="AI Video Camera (Minh họa nghệ thuật tùy chọn)",
        description=(
            "Chế độ sinh video bằng mô hình AI khuếch tán (Wan2.2 / ComfyUI). "
            "Chỉ dùng cho các cảnh minh họa phối cảnh nghệ thuật. "
            "KHÔNG bảo đảm độ chính xác kích thước hình học công trình."
        ),
        is_3d_geometry=False,
        preserves_technical_geometry=False,
        min_assets=1,
        max_safe_zoom=1.5,
        max_pan_velocity=0.35,
        requires_cuda=True,
        fallback_mode=CameraModeType.IMAGE_2D.value,
    ),
}


def get_camera_modes_catalog() -> list[dict[str, Any]]:
    """Return the declared capabilities, limitations, and fallback behavior for all camera modes."""
    caps = get_capabilities()
    geometry_ready = bool(caps["geometry"]["available"])

    items = []
    for info in CAMERA_MODES.values():
        item = info.to_dict()
        if info.mode == CameraModeType.SCENE_3D.value:
            item["available_now"] = geometry_ready
            item["availability_reason"] = (
                "Sẵn sàng hoạt động" if geometry_ready else "Thiếu GPU CUDA hoặc COLMAP/3DGS"
            )
        elif info.mode == CameraModeType.AI_VIDEO.value:
            item["available_now"] = False  # Disabled by default in core engine
            item["availability_reason"] = "AI adapter tùy chọn (mặc định tắt để bảo vệ hình học kỹ thuật)"
        else:
            item["available_now"] = True
            item["availability_reason"] = "Luôn sẵn sàng trên CPU"
        items.append(item)
    return items


def validate_camera_motion(
    mode: str,
    motion_config: dict[str, Any],
    scene_proxy: Any = None,
) -> tuple[bool, list[str]]:
    """Validate motion parameters according to the chosen camera mode's quality gates.

    Returns:
        (is_valid, rejection_reasons)
    """
    reasons: list[str] = []

    if mode not in CAMERA_MODES:
        return False, [f"Chế độ camera '{mode}' không hợp lệ. Phải là một trong: {list(CAMERA_MODES.keys())}"]

    info = CAMERA_MODES[mode]

    if mode == CameraModeType.IMAGE_2D.value:
        scale = float(motion_config.get("end_scale", 1.0))
        if scale > info.max_safe_zoom:
            reasons.append(
                f"Tỷ lệ phóng to ({scale:.2f}x) vượt quá giới hạn an toàn 2D ({info.max_safe_zoom:.2f}x) "
                f"gây vỡ hạt bản vẽ kỹ thuật."
            )
        start_scale = float(motion_config.get("start_scale", 1.0))
        if start_scale <= 0.0 or scale <= 0.0:
            reasons.append("Tỷ lệ scale phải lớn hơn 0.")

        pan_v = float(motion_config.get("pan_velocity", 0.0))
        if pan_v > info.max_pan_velocity:
            reasons.append(
                f"Vận tốc lia camera ({pan_v:.2f}) vượt quá mức an toàn ({info.max_pan_velocity:.2f}) gây giật khung hình."
            )

    elif mode == CameraModeType.SCENE_3D.value:
        caps = get_capabilities()
        if not caps["geometry"]["available"]:
            reasons.append(
                f"3D Scene Camera yêu cầu COLMAP và GPU CUDA nhưng hiện tại chưa khả dụng: "
                f"{caps['geometry']['reconstruct_reason'] or 'Chưa cài đặt'}. Hãy dùng {info.fallback_mode}."
            )

        ang_vel = float(motion_config.get("angular_velocity_deg_sec", 0.0))
        if ang_vel > 45.0:
            reasons.append(f"Vận tốc góc ({ang_vel:.1f} deg/s) vượt quá ngưỡng an toàn 45 deg/s.")

    elif mode == CameraModeType.AI_VIDEO.value:
        reasons.append("AI Video Camera là chế độ tùy chọn và chưa được bật trong cấu hình môi trường.")

    return len(reasons) == 0, reasons

