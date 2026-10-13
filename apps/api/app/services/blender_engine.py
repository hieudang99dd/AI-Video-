from __future__ import annotations

import json
import logging
from pathlib import Path
import subprocess
from typing import Any

from app.services.capabilities import get_capabilities

logger = logging.getLogger(__name__)


def generate_blender_python_script(
    shot_id: str,
    shot_name: str,
    camera_plan: dict[str, Any],
    image_paths: list[Path],
    output_mp4_path: Path,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    point_cloud_path: Path | None = None,
    mesh_path: Path | None = None,
) -> str:
    """Generate a reproducible Blender headless Python script (bpy) for the shot.

    Can be executed directly via:
        blender -b -P scene_render.py
    """
    duration_sec = float(camera_plan.get("duration_sec", 5.0))
    total_frames = max(2, int(duration_sec * fps))
    fov_deg = float(camera_plan.get("fov_deg", 50.0))
    trajectory = list(camera_plan.get("trajectory") or [])

    escaped_images = [str(p.resolve()).replace("\\", "/") for p in image_paths]
    escaped_out = str(output_mp4_path.resolve()).replace("\\", "/")
    escaped_pc = str(point_cloud_path.resolve()).replace("\\", "/") if point_cloud_path and point_cloud_path.exists() else ""
    escaped_mesh = str(mesh_path.resolve()).replace("\\", "/") if mesh_path and mesh_path.exists() else ""
    traj_json = json.dumps(trajectory, indent=2)

    script = f'''#!/usr/bin/env python3
"""Auto-generated Blender Headless 3D Infrastructure Scene Script
Shot ID: {shot_id}
Shot Name: {shot_name}
Source Mode: {camera_plan.get("source_mode", "C_SINGLE_IMAGE_2_5D")}
Preset: {camera_plan.get("preset", "establishing_shot")}
Scale Status: uncalibrated (relative_units)
Usage: blender -b -P scene_render.py
"""
import math
import json
from pathlib import Path
import bpy

# 1. Reset scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = {fps}
scene.frame_start = 1
scene.frame_end = {total_frames}
scene.render.resolution_x = {width}
scene.render.resolution_y = {height}
scene.render.resolution_percentage = 100

# 2. World & Sun Lighting (Civil/InfraWorks Daylight)
world = bpy.data.worlds.new("InfraWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = (0.05, 0.08, 0.12, 1.0)
    bg_node.inputs[1].default_value = 1.0

sun_data = bpy.data.lights.new(name="SunLight", type="SUN")
sun_data.energy = 3.5
sun_obj = bpy.data.objects.new(name="SunLight", object_data=sun_data)
scene.collection.objects.link(sun_obj)
sun_obj.location = (10.0, -15.0, 25.0)
sun_obj.rotation_euler = (math.radians(45.0), math.radians(15.0), math.radians(30.0))

# 3. Load 3D Mesh / Point Cloud or Create Multi-Plane 2.5D/3D Image Plates
mesh_path = "{escaped_mesh}"
point_cloud_path = "{escaped_pc}"
image_paths = {json.dumps(escaped_images)}

if mesh_path and Path(mesh_path).exists():
    if mesh_path.lower().endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=mesh_path)
    elif mesh_path.lower().endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=mesh_path)
elif point_cloud_path and Path(point_cloud_path).exists() and point_cloud_path.lower().endswith(".ply"):
    bpy.ops.wm.ply_import(filepath=point_cloud_path)

for idx, img_file in enumerate(image_paths):
    if not Path(img_file).exists():
        continue
    bpy.ops.mesh.primitive_plane_add(size=16.0, location=(0.0, idx * 4.5, 2.5), rotation=(math.radians(90.0), 0.0, 0.0))
    plane = bpy.context.active_object
    plane.name = f"InfraPlate_{{idx:02d}}"
    plane.scale = (1.0, 9.0 / 16.0, 1.0)
    mat = bpy.data.materials.new(name=f"PlateMat_{{idx:02d}}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(img_file)
    if bsdf:
        mat.node_tree.links.new(bsdf.inputs["Base Color"], tex_node.outputs["Color"])
    plane.data.materials.append(mat)

# 4. Create & Animate Camera Trajectory with Quaternion SLERP Keyframes
cam_data = bpy.data.cameras.new(name="InfraCamera")
cam_data.lens_unit = "FOV"
cam_data.angle = math.radians({fov_deg})
cam_obj = bpy.data.objects.new(name="InfraCamera", object_data=cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_obj.rotation_mode = "QUATERNION"

trajectory = json.loads("""{traj_json}""")
n_samples = max(1, len(trajectory))
for i, sample in enumerate(trajectory):
    frame_num = 1 + int(round((i / max(1, n_samples - 1)) * ({total_frames} - 1)))
    pos = sample.get("position", [0.0, -8.0, 3.0])
    quat = sample.get("quaternion_wxyz", [1.0, 0.0, 0.0, 0.0])
    cam_obj.location = (float(pos[0]), float(pos[1]), float(pos[2]))
    cam_obj.rotation_quaternion = (float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3]))
    cam_obj.keyframe_insert(data_path="location", frame=frame_num)
    cam_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame_num)

# 5. Configure Output & Render
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath = "{escaped_out}"

if __name__ == "__main__":
    bpy.ops.render.render(animation=True)
'''
    return script


def export_and_optionally_run_blender_scene(
    shot_id: str,
    shot_name: str,
    camera_plan: dict[str, Any],
    image_paths: list[Path],
    workdir: Path,
    output_mp4_path: Path,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    execute_if_available: bool = True,
    point_cloud_path: Path | None = None,
    mesh_path: Path | None = None,
) -> dict[str, Any]:
    """Write ``scene_render.py`` and ``camera_trajectory.json`` to ``workdir``.

    If Blender CLI is available on the system and ``execute_if_available`` is True,
    executes ``blender -b -P scene_render.py``. Otherwise records explicit provenance
    that the script was exported and the 2.5D/3D plate renderer should be used.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    script_path = workdir / f"shot_{shot_id}_blender.py"
    trajectory_path = workdir / f"shot_{shot_id}_camera_trajectory.json"

    script_text = generate_blender_python_script(
        shot_id=shot_id,
        shot_name=shot_name,
        camera_plan=camera_plan,
        image_paths=image_paths,
        output_mp4_path=output_mp4_path,
        width=width,
        height=height,
        fps=fps,
        point_cloud_path=point_cloud_path,
        mesh_path=mesh_path,
    )
    script_path.write_text(script_text, encoding="utf-8")
    trajectory_path.write_text(json.dumps(camera_plan, indent=2, ensure_ascii=False), encoding="utf-8")

    caps = get_capabilities()
    blender_info = caps.get("blender", {})
    blender_exe = blender_info.get("path")

    executed = False
    execution_error = None
    if execute_if_available and blender_exe:
        try:
            subprocess.run(
                [blender_exe, "-b", "-P", str(script_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            executed = output_mp4_path.exists() and output_mp4_path.stat().st_size > 1024
        except Exception as exc:
            execution_error = str(exc)
            logger.warning("Blender CLI execution failed for shot %s: %s", shot_id, exc)

    return {
        "shot_id": shot_id,
        "blender_script_path": str(script_path),
        "camera_trajectory_path": str(trajectory_path),
        "blender_cli_available": bool(blender_exe),
        "blender_cli_executed": executed,
        "execution_error": execution_error,
        "fallback_renderer": None if executed else "projection_plate_2_5d_ffmpeg",
        "note": (
            "Rendered directly via Blender Headless CLI."
            if executed
            else "Blender script (.py) and camera trajectory (.json) exported; using FFmpeg 2.5D/3D plate renderer because Blender CLI is not installed on PATH."
        ),
    }
