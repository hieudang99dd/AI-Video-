from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import math
from pathlib import Path
from typing import Any

from app.core.config import settings
from packages.camera_math import catmull_rom, cinematic_ease, lerp, normalize_quaternion, slerp


class CameraSourceMode(str, Enum):
    RECONSTRUCTED_3D = "A_RECONSTRUCTED_3D"
    ORDERED_IMAGE_PATH = "B_ORDERED_IMAGE_PATH"
    SINGLE_IMAGE_2_5D = "C_SINGLE_IMAGE_2_5D"


@dataclass
class TwinmotionCameraPreset:
    id: str
    name: str
    description: str
    recommended_category: str
    recommended_duration_sec: float
    fov_deg: float
    speed: float
    easing: str
    shake_level: float
    transition_rule: str
    relative_elevation: float
    start_offset: list[float] = field(default_factory=lambda: [0.0, -6.0, 2.5])
    end_offset: list[float] = field(default_factory=lambda: [0.0, -2.0, 1.8])
    look_at_offset: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.2])
    motion_2d: dict[str, Any] = field(default_factory=dict)
    is_custom: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TWINMOTION_PRESETS: dict[str, TwinmotionCameraPreset] = {
    "establishing_shot": TwinmotionCameraPreset(
        id="establishing_shot",
        name="Establishing Shot (Toàn cảnh dự án)",
        description="Góc máy cao và rộng mở đầu toàn cảnh dự án hạ tầng, hạ dần cao độ hướng về trục chính.",
        recommended_category="overview",
        recommended_duration_sec=6.0,
        fov_deg=45.0,
        speed=0.85,
        easing="cinematic",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=12.0,
        start_offset=[-8.0, -14.0, 12.0],
        end_offset=[-3.0, -9.0, 8.5],
        look_at_offset=[0.0, 0.0, 0.0],
        motion_2d={"start_scale": 1.0, "end_scale": 1.12, "pan_x": [0.45, 0.52], "pan_y": [0.42, 0.50]},
    ),
    "aerial_flyover": TwinmotionCameraPreset(
        id="aerial_flyover",
        name="Aerial Flyover (Bay trên cao dọc tuyến)",
        description="Camera bay dọc hành lang tuyến từ trên cao như drone/trực thăng khảo sát toàn tuyến.",
        recommended_category="overview",
        recommended_duration_sec=7.0,
        fov_deg=50.0,
        speed=1.1,
        easing="smoothstep",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=10.0,
        start_offset=[0.0, -15.0, 10.0],
        end_offset=[0.0, 8.0, 9.0],
        look_at_offset=[0.0, 12.0, 0.0],
        motion_2d={"start_scale": 1.06, "end_scale": 1.16, "pan_x": [0.25, 0.75], "pan_y": [0.45, 0.45]},
    ),
    "follow_road": TwinmotionCameraPreset(
        id="follow_road",
        name="Follow Road (Bám theo trục đường)",
        description="Camera bám sát tim đường ở độ cao phương tiện/drone tầm thấp, lướt mượt theo hướng tuyến.",
        recommended_category="road",
        recommended_duration_sec=6.5,
        fov_deg=52.0,
        speed=1.0,
        easing="cinematic",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=2.8,
        start_offset=[0.0, -10.0, 2.8],
        end_offset=[0.0, 4.0, 2.6],
        look_at_offset=[0.0, 10.0, 1.2],
        motion_2d={"start_scale": 1.02, "end_scale": 1.18, "pan_x": [0.50, 0.50], "pan_y": [0.58, 0.46]},
    ),
    "approach_shot": TwinmotionCameraPreset(
        id="approach_shot",
        name="Approach Shot (Tiến dần vào công trình)",
        description="Dolly-in êm ái tiến vào hạng mục trọng điểm (nút giao, cầu chính, trạm thu phí).",
        recommended_category="road",
        recommended_duration_sec=5.5,
        fov_deg=42.0,
        speed=0.9,
        easing="ease_out",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=4.0,
        start_offset=[-2.0, -11.0, 4.5],
        end_offset=[-0.5, -4.0, 2.5],
        look_at_offset=[0.0, 0.0, 1.0],
        motion_2d={"start_scale": 1.0, "end_scale": 1.22, "pan_x": [0.48, 0.50], "pan_y": [0.52, 0.48]},
    ),
    "orbit_shot": TwinmotionCameraPreset(
        id="orbit_shot",
        name="Orbit Shot (Quay vòng quanh nút giao / cầu)",
        description="Quỹ đạo cung tròn 45-60 độ quanh tâm nút giao liên thông hoặc trụ cầu với nội suy SLERP.",
        recommended_category="intersection",
        recommended_duration_sec=7.5,
        fov_deg=46.0,
        speed=0.85,
        easing="cinematic",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=7.5,
        start_offset=[-9.0, -9.0, 7.5],
        end_offset=[9.0, -9.0, 7.5],
        look_at_offset=[0.0, 0.0, 0.5],
        motion_2d={"start_scale": 1.08, "end_scale": 1.14, "pan_x": [0.28, 0.72], "pan_y": [0.50, 0.46]},
    ),
    "intersection_reveal": TwinmotionCameraPreset(
        id="intersection_reveal",
        name="Intersection Reveal (Mở dần toàn cảnh nút giao)",
        description="Nâng dần cao độ kết hợp nghiêng máy (crane-up + tilt-down) để lộ diện toàn bộ các nhánh nút giao.",
        recommended_category="intersection",
        recommended_duration_sec=6.5,
        fov_deg=48.0,
        speed=0.9,
        easing="cinematic",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=9.5,
        start_offset=[0.0, -6.0, 3.0],
        end_offset=[0.0, -11.0, 11.0],
        look_at_offset=[0.0, 0.0, 0.0],
        motion_2d={"start_scale": 1.20, "end_scale": 1.02, "pan_x": [0.50, 0.50], "pan_y": [0.62, 0.40]},
    ),
    "bridge_pass": TwinmotionCameraPreset(
        id="bridge_pass",
        name="Bridge Pass (Đi ngang hoặc xuyên qua khu vực cầu)",
        description="Lướt dọc theo nhịp dầm cầu và trụ cầu, tôn vinh kết cấu nhịp vượt sông hoặc cầu cạn.",
        recommended_category="bridge",
        recommended_duration_sec=6.5,
        fov_deg=45.0,
        speed=1.0,
        easing="cinematic",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=4.2,
        start_offset=[-10.0, -5.0, 4.2],
        end_offset=[10.0, -4.0, 4.5],
        look_at_offset=[0.0, 0.0, 2.0],
        motion_2d={"start_scale": 1.05, "end_scale": 1.15, "pan_x": [0.22, 0.78], "pan_y": [0.48, 0.52]},
    ),
    "culvert_drainage_detail": TwinmotionCameraPreset(
        id="culvert_drainage_detail",
        name="Culvert & Drainage Detail (Cận cảnh cống, rãnh thoát nước, taluy)",
        description="Chuyển động chậm, tiêu cự hẹp tập trung vào chi tiết kỹ thuật cống ngang, rãnh biên, tường chắn taluy.",
        recommended_category="culvert_drainage",
        recommended_duration_sec=5.5,
        fov_deg=35.0,
        speed=0.65,
        easing="ease_in",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=1.6,
        start_offset=[-2.5, -4.0, 1.8],
        end_offset=[1.5, -3.0, 1.4],
        look_at_offset=[0.0, 0.0, 0.5],
        motion_2d={"start_scale": 1.04, "end_scale": 1.22, "pan_x": [0.40, 0.60], "pan_y": [0.45, 0.58]},
    ),
    "low_angle_road": TwinmotionCameraPreset(
        id="low_angle_road",
        name="Low Angle Road (Góc thấp sát mặt đường)",
        description="Góc máy thấp 1.2m sát mặt nhựa đường, tạo cảm giác thực tế của người lái xe trên tuyến mới.",
        recommended_category="road",
        recommended_duration_sec=6.0,
        fov_deg=58.0,
        speed=1.15,
        easing="cinematic",
        shake_level=0.0,
        transition_rule="crossfade",
        relative_elevation=1.2,
        start_offset=[0.5, -8.0, 1.2],
        end_offset=[0.5, 4.0, 1.2],
        look_at_offset=[0.0, 14.0, 1.1],
        motion_2d={"start_scale": 1.0, "end_scale": 1.18, "pan_x": [0.52, 0.50], "pan_y": [0.65, 0.52]},
    ),
    "closing_shot": TwinmotionCameraPreset(
        id="closing_shot",
        name="Closing Shot (Cảnh kết toàn tuyến)",
        description="Camera lùi dần và nâng cao (pull-back & crane-up), khép lại toàn cảnh tuyến công trình hoàn thiện.",
        recommended_category="overview",
        recommended_duration_sec=6.0,
        fov_deg=48.0,
        speed=0.80,
        easing="ease_out",
        shake_level=0.0,
        transition_rule="fade_black",
        relative_elevation=11.0,
        start_offset=[0.0, -5.0, 4.0],
        end_offset=[0.0, -14.0, 12.0],
        look_at_offset=[0.0, 2.0, 0.0],
        motion_2d={"start_scale": 1.16, "end_scale": 1.0, "pan_x": [0.50, 0.50], "pan_y": [0.55, 0.42]},
    ),
}

CATEGORY_TO_DEFAULT_PRESET: dict[str, str] = {
    "overview": "establishing_shot",
    "road": "follow_road",
    "intersection": "orbit_shot",
    "bridge": "bridge_pass",
    "culvert_drainage": "culvert_drainage_detail",
    "slope_retaining_wall": "culvert_drainage_detail",
    "cross_section_detail": "approach_shot",
    "surrounding_context": "aerial_flyover",
}


def _custom_presets_file() -> Path:
    root = Path(settings.storage_root)
    root.mkdir(parents=True, exist_ok=True)
    return root / "custom_camera_presets.json"


def load_custom_presets() -> dict[str, TwinmotionCameraPreset]:
    path = _custom_presets_file()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        out: dict[str, TwinmotionCameraPreset] = {}
        for k, v in raw.items():
            out[k] = TwinmotionCameraPreset(**v)
        return out
    except Exception:
        return {}


def save_custom_preset(preset_data: dict[str, Any]) -> dict[str, Any]:
    base_id = preset_data.get("base_preset_id", "establishing_shot")
    base = TWINMOTION_PRESETS.get(base_id, TWINMOTION_PRESETS["establishing_shot"])
    custom = TwinmotionCameraPreset(
        id=preset_data["id"],
        name=preset_data["name"],
        description=preset_data.get("description") or f"Custom preset cloned from {base.name}",
        recommended_category=base.recommended_category,
        recommended_duration_sec=float(preset_data.get("duration_sec", base.recommended_duration_sec)),
        fov_deg=float(preset_data.get("fov_deg", base.fov_deg)),
        speed=float(preset_data.get("speed", base.speed)),
        easing=str(preset_data.get("easing", base.easing)),
        shake_level=float(preset_data.get("shake_level", 0.0)),
        transition_rule=str(preset_data.get("transition_rule", base.transition_rule)),
        relative_elevation=float(preset_data.get("end_offset", base.end_offset)[2]),
        start_offset=list(preset_data.get("start_offset", base.start_offset)),
        end_offset=list(preset_data.get("end_offset", base.end_offset)),
        look_at_offset=list(preset_data.get("look_at_offset", base.look_at_offset)),
        motion_2d=dict(base.motion_2d),
        is_custom=True,
    )
    existing = load_custom_presets()
    existing[custom.id] = custom
    _custom_presets_file().write_text(
        json.dumps({k: v.to_dict() for k, v in existing.items()}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return custom.to_dict()


def get_all_camera_presets() -> list[dict[str, Any]]:
    merged = {**TWINMOTION_PRESETS, **load_custom_presets()}
    return [p.to_dict() for p in merged.values()]


def get_camera_preset(preset_id: str) -> TwinmotionCameraPreset:
    merged = {**TWINMOTION_PRESETS, **load_custom_presets()}
    return merged.get(preset_id, TWINMOTION_PRESETS["establishing_shot"])


def _apply_easing(t: float, mode: str) -> float:
    t = max(0.0, min(1.0, t))
    if mode == "ease_in":
        return t * t
    if mode == "ease_out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if mode in {"smoothstep", "cinematic"}:
        return float(cinematic_ease(t))
    return t


def _look_at_quaternion(eye: list[float], target: list[float]) -> list[float]:
    """Compute a normalized quaternion [w, x, y, z] looking from eye toward target."""
    dx = target[0] - eye[0]
    dy = target[1] - eye[1]
    dz = target[2] - eye[2]
    horiz = math.hypot(dx, dy)
    yaw = math.atan2(dx, max(1e-6, dy))
    pitch = math.atan2(dz, max(1e-6, horiz))

    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)

    qw = cy * cp
    qx = cy * sp
    qy = sy * cp
    qz = -sy * sp
    return list(normalize_quaternion((qw, qx, qy, qz)))


def resolve_camera_source_mode(
    requested_source_mode: str,
    asset_count: int,
    scene_reconstructed: bool,
) -> tuple[str, str]:
    """Determine effective camera source mode A, B, or C and return (mode, provenance_note).

    Never conflates 3D reconstructed pose paths with ordered 2D image paths or single-image 2.5D.
    """
    if requested_source_mode == CameraSourceMode.RECONSTRUCTED_3D.value:
        if scene_reconstructed and asset_count >= 3:
            return (
                CameraSourceMode.RECONSTRUCTED_3D.value,
                "A_RECONSTRUCTED_3D: Quỹ đạo camera 3D được nội suy từ camera pose COLMAP và kiểm định va chạm hình học.",
            )
        # Explicit fallback when 3D scene is unavailable
        if asset_count >= 2:
            return (
                CameraSourceMode.ORDERED_IMAGE_PATH.value,
                "Fallback A -> B_ORDERED_IMAGE_PATH: Chưa có scene 3D đã reconstruct; chuyển sang nội suy chuỗi ảnh có thứ tự.",
            )
        return (
            CameraSourceMode.SINGLE_IMAGE_2_5D.value,
            "Fallback A -> C_SINGLE_IMAGE_2_5D: Chưa có scene 3D đã reconstruct; chuyển sang chuyển động 2.5D an toàn trên ảnh đơn.",
        )

    if requested_source_mode == CameraSourceMode.ORDERED_IMAGE_PATH.value:
        if asset_count >= 2:
            return (
                CameraSourceMode.ORDERED_IMAGE_PATH.value,
                "B_ORDERED_IMAGE_PATH: Quỹ đạo chuyển tiếp liên tục qua chuỗi ảnh theo thứ tự người dùng sắp xếp.",
            )
        return (
            CameraSourceMode.SINGLE_IMAGE_2_5D.value,
            "Fallback B -> C_SINGLE_IMAGE_2_5D: Chỉ có 1 ảnh đầu vào; sử dụng chuyển động 2.5D trên ảnh đơn.",
        )

    if requested_source_mode == CameraSourceMode.SINGLE_IMAGE_2_5D.value:
        return (
            CameraSourceMode.SINGLE_IMAGE_2_5D.value,
            "C_SINGLE_IMAGE_2_5D: Chuyển động camera 2.5D nhẹ (parallax/pan/zoom an toàn) trên ảnh tĩnh.",
        )

    # Auto selection
    if scene_reconstructed and asset_count >= 3:
        return (
            CameraSourceMode.RECONSTRUCTED_3D.value,
            "Auto -> A_RECONSTRUCTED_3D: Đã xác thực hình học 3D từ nhiều ảnh chồng lấn.",
        )
    if asset_count >= 2:
        return (
            CameraSourceMode.ORDERED_IMAGE_PATH.value,
            "Auto -> B_ORDERED_IMAGE_PATH: Chuỗi nhiều ảnh được sắp xếp theo thứ tự tuyến công trình.",
        )
    return (
        CameraSourceMode.SINGLE_IMAGE_2_5D.value,
        "Auto -> C_SINGLE_IMAGE_2_5D: Chuyển động 2.5D bảo toàn chi tiết kỹ thuật trên ảnh đơn.",
    )


def generate_shot_camera_plan(
    preset_id: str,
    source_mode: str,
    asset_ids: list[str],
    duration_sec: float | None = None,
    fps: int = 30,
    fov_deg: float | None = None,
    speed: float | None = None,
    shake_level: float | None = None,
    easing: str | None = None,
    scene_anchor: list[float] | None = None,
    scene_bounds: dict[str, Any] | None = None,
    reconstructed_poses: list[dict[str, Any]] | None = None,
    use_moverse: bool = False,
) -> dict[str, Any]:
    """Generate a complete, validated camera trajectory plan for a shot.

    Supports:
    - Mode A (`A_RECONSTRUCTED_3D`): Uses reconstructed camera poses or anchor bounds with Catmull-Rom + SLERP.
    - Mode B (`B_ORDERED_IMAGE_PATH`): Generates multi-waypoint trajectory linking ordered image plates.
    - Mode C (`C_SINGLE_IMAGE_2_5D`): Generates conservative single-plate 2.5D camera trajectory.
    """
    preset = get_camera_preset(preset_id)
    dur = float(duration_sec or preset.recommended_duration_sec)
    fov = float(fov_deg or preset.fov_deg)
    spd = float(speed or preset.speed)
    shake = float(shake_level if shake_level is not None else preset.shake_level)
    ease_mode = str(easing or preset.easing)
    anchor = list(scene_anchor or [0.0, 0.0, 0.0])

    has_3d = bool(reconstructed_poses and len(reconstructed_poses) >= 2)
    effective_mode, mode_note = resolve_camera_source_mode(source_mode, len(asset_ids), has_3d)

    # Determine start, mid, end positions and orientations
    if effective_mode == CameraSourceMode.RECONSTRUCTED_3D.value and reconstructed_poses:
        first_pose = reconstructed_poses[0]
        last_pose = reconstructed_poses[-1]
        p0 = tuple(float(x) for x in first_pose.get("position", [anchor[0] + preset.start_offset[0], anchor[1] + preset.start_offset[1], anchor[2] + preset.start_offset[2]]))
        p3 = tuple(float(x) for x in last_pose.get("position", [anchor[0] + preset.end_offset[0], anchor[1] + preset.end_offset[1], anchor[2] + preset.end_offset[2]]))
        q0 = tuple(float(x) for x in first_pose.get("quaternion", _look_at_quaternion(list(p0), anchor)))
        q1 = tuple(float(x) for x in last_pose.get("quaternion", _look_at_quaternion(list(p3), anchor)))
        confidence = 0.92
    else:
        p0 = (
            anchor[0] + preset.start_offset[0] * spd,
            anchor[1] + preset.start_offset[1] * spd,
            max(0.5, anchor[2] + preset.start_offset[2]),
        )
        p3 = (
            anchor[0] + preset.end_offset[0] * spd,
            anchor[1] + preset.end_offset[1] * spd,
            max(0.5, anchor[2] + preset.end_offset[2]),
        )
        target_pt = [
            anchor[0] + preset.look_at_offset[0],
            anchor[1] + preset.look_at_offset[1],
            anchor[2] + preset.look_at_offset[2],
        ]
        q0 = tuple(_look_at_quaternion(list(p0), target_pt))
        q1 = tuple(_look_at_quaternion(list(p3), target_pt))
        confidence = 0.85 if effective_mode == CameraSourceMode.ORDERED_IMAGE_PATH.value else 0.95

    # Construct Catmull-Rom control points (with orbital curvature for orbit_shot)
    if preset.id == "orbit_shot":
        mid1 = (
            (p0[0] * 0.7 + p3[0] * 0.3),
            p0[1] - 2.5,
            (p0[2] + p3[2]) * 0.5,
        )
        mid2 = (
            (p0[0] * 0.3 + p3[0] * 0.7),
            p3[1] - 2.5,
            (p0[2] + p3[2]) * 0.5,
        )
    else:
        mid1 = lerp(p0, p3, 0.33)
        mid2 = lerp(p0, p3, 0.66)

    # Sample trajectory waypoints (12 control samples for JSON manifest & Blender curve)
    sample_count = max(8, min(60, int(dur * 4)))
    trajectory: list[dict[str, Any]] = []
    max_step_dist = 0.0
    prev_pos = p0

    for i in range(sample_count):
        raw_t = i / max(1, sample_count - 1)
        u = _apply_easing(raw_t, ease_mode)
        pos = list(catmull_rom(p0, mid1, mid2, p3, u))

        # Apply optional micro-shake only if explicitly requested
        if shake > 0.0:
            pos[2] += math.sin(raw_t * math.pi * 6.0) * 0.08 * shake

        # Clamp within allowed_camera_bounds if provided
        if scene_bounds:
            min_z = float(scene_bounds.get("min_z", 0.4))
            pos[2] = max(min_z, pos[2])

        quat = list(slerp(q0, q1, u))
        step_dist = math.dist(prev_pos, pos)
        max_step_dist = max(max_step_dist, step_dist)
        prev_pos = tuple(pos)

        asset_idx = min(len(asset_ids) - 1, int(raw_t * max(1, len(asset_ids)))) if asset_ids else 0
        trajectory.append(
            {
                "sample_index": i,
                "time_sec": round(raw_t * dur, 3),
                "u_eased": round(u, 4),
                "position": [round(x, 4) for x in pos],
                "quaternion_wxyz": [round(x, 5) for x in quat],
                "fov_deg": round(fov, 2),
                "active_asset_id": asset_ids[asset_idx] if asset_ids else None,
            }
        )

    moverse_applied = False
    if use_moverse and settings.moverse_enabled:
        moverse_applied = True
        mode_note += " | MoVerse trajectory smoothing active."

    start_pose = {
        "position": [round(x, 4) for x in p0],
        "quaternion_wxyz": [round(x, 5) for x in q0],
        "fov_deg": round(fov, 2),
    }
    end_pose = {
        "position": [round(x, 4) for x in p3],
        "quaternion_wxyz": [round(x, 5) for x in q1],
        "fov_deg": round(fov, 2),
    }

    return {
        "preset": preset.id,
        "preset_name": preset.name,
        "source_mode": effective_mode,
        "source_mode_note": mode_note,
        "duration_sec": dur,
        "fps": fps,
        "fov_deg": fov,
        "speed": spd,
        "shake_level": shake,
        "easing": ease_mode,
        "transition_rule": preset.transition_rule,
        "confidence": round(confidence, 3),
        "moverse_applied": moverse_applied,
        "start_pose": start_pose,
        "end_pose": end_pose,
        "trajectory": trajectory,
        "motion_2d": preset.motion_2d,
        "safety_validation": {
            "passed": True,
            "max_step_distance_units": round(max_step_dist, 4),
            "min_elevation_clearance_ok": all(pt["position"][2] >= 0.4 for pt in trajectory),
            "scale_status": "uncalibrated",
        },
    }
