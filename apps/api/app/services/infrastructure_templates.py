from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class InfrastructureTemplate:
    id: str
    name: str
    description: str
    recommended_duration_sec: float
    recommended_camera_mode: str
    default_overlay_title: str
    default_subtitle: str
    default_narration: str
    motion_preset: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


INFRASTRUCTURE_TEMPLATES: list[InfrastructureTemplate] = [
    InfrastructureTemplate(
        id="project_overview",
        name="Tổng quan dự án (Project Overview)",
        description="Phối cảnh tổng thể từ InfraWorks, giới thiệu vị trí, chủ đầu tư, quy mô công trình.",
        recommended_duration_sec=6.0,
        recommended_camera_mode="2D_IMAGE_CAMERA",
        default_overlay_title="TỔNG QUAN DỰ ÁN HẠ TẦNG",
        default_subtitle="Quy hoạch tổng thể và phạm vi triển khai dự án",
        default_narration="Dự án hạ tầng kỹ thuật đóng vai trò huyết mạch trong mạng lưới kết nối giao thông khu vực.",
        motion_preset={"type": "pan_zoom", "start_scale": 1.0, "end_scale": 1.15, "direction": "center_zoom"},
    ),
    InfrastructureTemplate(
        id="alignment_plan",
        name="Bình đồ tuyến (Plan View / Alignment)",
        description="Bản vẽ bình đồ tuyến Civil 3D hiển thị tim tuyến, cọc lý trình, đường cong nằm và ranh GPMB.",
        recommended_duration_sec=7.0,
        recommended_camera_mode="2D_IMAGE_CAMERA",
        default_overlay_title="BÌNH ĐỒ HƯỚNG TUYẾN CHÍNH",
        default_subtitle="Lý trình tim tuyến: Km0+000 đến điểm cuối tuyến",
        default_narration="Hướng tuyến được tối ưu hóa theo quy chuẩn kỹ thuật, giảm thiểu tối đa khối lượng giải phóng mặt bằng.",
        motion_preset={"type": "pan", "start_scale": 1.08, "end_scale": 1.08, "direction": "left_to_right"},
    ),
    InfrastructureTemplate(
        id="profile_view",
        name="Trắc dọc thiết kế (Profile View)",
        description="Bản vẽ trắc dọc thể hiện đường đỏ thiết kế, độ dốc dọc, đường cong đứng và cao độ tự nhiên.",
        recommended_duration_sec=6.0,
        recommended_camera_mode="2D_IMAGE_CAMERA",
        default_overlay_title="TRẮC DỌC THIẾT KẾ",
        default_subtitle="Độ dốc dọc và cao độ khống chế kỹ thuật",
        default_narration="Đường đỏ thiết kế bám sát địa hình tự nhiên, bảo đảm độ dốc thoát nước và an toàn phương tiện lưu thông.",
        motion_preset={"type": "pan", "start_scale": 1.05, "end_scale": 1.05, "direction": "left_to_right"},
    ),
    InfrastructureTemplate(
        id="cross_sections",
        name="Mặt cắt ngang điển hình (Cross Sections)",
        description="Mặt cắt ngang thể hiện bề rộng làn xe, dải phân cách, mái taluy đào/đắp và kết cấu áo đường.",
        recommended_duration_sec=6.0,
        recommended_camera_mode="2D_IMAGE_CAMERA",
        default_overlay_title="MẶT CẮT NGANG ĐIỂN HÌNH",
        default_subtitle="Quy mô mặt cắt ngang: Làn cơ giới, lề đường và taluy",
        default_narration="Mặt cắt ngang được bố trí đầy đủ các dải an toàn, rãnh biên thu nước và kết cấu áo đường chịu tải trọng lớn.",
        motion_preset={"type": "zoom", "start_scale": 1.0, "end_scale": 1.20, "direction": "center_zoom"},
    ),
    InfrastructureTemplate(
        id="bridges_interchanges",
        name="Cầu, Cống & Nút giao (Bridges & Interchanges)",
        description="Mô phỏng 3D cầu vượt sông, cầu cạn, cống chui dân sinh và nút giao liên thông từ InfraWorks.",
        recommended_duration_sec=8.0,
        recommended_camera_mode="3D_SCENE_CAMERA",
        default_overlay_title="CÔNG TRÌNH CẦU & NÚT GIAO",
        default_subtitle="Nút giao khác mức và cầu vượt khẩu độ lớn",
        default_narration="Các nút giao liên thông và công trình vượt dòng bảo đảm lưu thông thông suốt và an toàn tuyệt đối.",
        motion_preset={"type": "orbit_flyby", "start_scale": 1.0, "end_scale": 1.25, "direction": "pan_up"},
    ),
    InfrastructureTemplate(
        id="drainage_system",
        name="Hệ thống thoát nước (Drainage System)",
        description="Mạng lưới cống thoát nước mưa, hố ga, cửa xả và mương dẫn dòng bảo vệ nền đường.",
        recommended_duration_sec=6.0,
        recommended_camera_mode="2D_IMAGE_CAMERA",
        default_overlay_title="HỆ THỐNG THOÁT NƯỚC KỸ THUẬT",
        default_subtitle="Mạng lưới cống dọc, cống ngang và cửa xả",
        default_narration="Hệ thống thoát nước mặt và ngầm được tính toán thủy lực kỹ lưỡng, ngăn ngừa ngập úng và xói lở taluy.",
        motion_preset={"type": "pan", "start_scale": 1.06, "end_scale": 1.06, "direction": "top_to_bottom"},
    ),
    InfrastructureTemplate(
        id="traffic_safety",
        name="An toàn giao thông & Chiếu sáng (Traffic Safety)",
        description="Hệ thống vạch sơn kẻ đường, biển báo, hộ lan mềm, dải phân cách và chiếu sáng ban đêm.",
        recommended_duration_sec=6.0,
        recommended_camera_mode="2D_IMAGE_CAMERA",
        default_overlay_title="AN TOÀN GIAO THÔNG & CHIẾU SÁNG",
        default_subtitle="Biển báo chỉ dẫn, hộ lan tôn sóng và hệ thống đèn",
        default_narration="Hạng mục an toàn giao thông đáp ứng quy chuẩn quốc gia, nâng cao tầm nhìn và giảm thiểu rủi ro tai nạn.",
        motion_preset={"type": "pan_zoom", "start_scale": 1.0, "end_scale": 1.15, "direction": "slow_pan"},
    ),
    InfrastructureTemplate(
        id="project_outro",
        name="Kết thúc & Thông tin dự án (Project Outro)",
        description="Tổng kết tiến độ dự án, thông điệp cam kết, thông tin chủ đầu tư và đơn vị tư vấn thiết kế.",
        recommended_duration_sec=5.0,
        recommended_camera_mode="2D_IMAGE_CAMERA",
        default_overlay_title="THÔNG TIN DỰ ÁN & TIẾN ĐỘ",
        default_subtitle="Chủ đầu tư - Đơn vị tư vấn thiết kế và giám sát",
        default_narration="Công trình dự kiến hoàn thành đúng tiến độ, đóng góp tích cực vào sự phát triển kinh tế hạ tầng địa phương.",
        motion_preset={"type": "zoom", "start_scale": 1.10, "end_scale": 1.0, "direction": "fade_outro"},
    ),
]


def get_infrastructure_templates() -> list[dict[str, Any]]:
    """Return all 8 standard infrastructure video templates."""
    return [t.to_dict() for t in INFRASTRUCTURE_TEMPLATES]


def get_template_by_id(template_id: str) -> dict[str, Any] | None:
    """Retrieve a specific template by its identifier."""
    for t in INFRASTRUCTURE_TEMPLATES:
        if t.id == template_id:
            return t.to_dict()
    return None


def generate_infrastructure_storyboard(project_name: str, asset_ids: list[str]) -> list[dict[str, Any]]:
    """Map a collection of uploaded assets into an initial infrastructure storyboard.

    Assets are assigned to templates in sequence. If fewer assets are uploaded than
    templates, remaining templates reuse available assets. If more assets are present,
    they are distributed across the shots.
    """
    if not asset_ids:
        return []

    storyboard: list[dict[str, Any]] = []
    template_count = len(INFRASTRUCTURE_TEMPLATES)

    for idx, tpl in enumerate(INFRASTRUCTURE_TEMPLATES):
        # Distribute assets evenly across templates
        asset_idx = idx % len(asset_ids)
        current_asset = asset_ids[asset_idx]

        overlay = tpl.default_overlay_title
        if idx == 0 and project_name:
            overlay = f"{project_name.upper()} - {tpl.default_overlay_title}"

        shot_item = {
            "name": f"Shot {idx + 1:02d}: {tpl.name.split(' (')[0]}",
            "template_id": tpl.id,
            "asset_ids": [current_asset],
            "duration_sec": tpl.recommended_duration_sec,
            "fps": 30,
            "mode": "auto",
            "camera_mode": tpl.recommended_camera_mode,
            "easing": "cinematic",
            "overlay_title": overlay,
            "subtitle_text": tpl.default_subtitle,
            "narration_text": tpl.default_narration,
            "motion_preset": tpl.motion_preset,
        }
        storyboard.append(shot_item)

    return storyboard
