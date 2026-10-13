from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from app.core.config import settings


def _resolve_ffmpeg() -> str | None:
    found = shutil.which(settings.ffmpeg_path) or shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return str(exe)
    except Exception:
        pass
    return None


def _probe_nvidia_smi() -> dict:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        win_smi = Path(r"C:\Windows\System32\nvidia-smi.exe")
        if win_smi.exists():
            nvidia_smi = str(win_smi)
    if not nvidia_smi:
        return {
            "available": False,
            "gpu_name": None,
            "vram_total_gb": 0.0,
            "vram_free_gb": 0.0,
            "driver_version": None,
        }
    try:
        proc = subprocess.run(
            [
                nvidia_smi,
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        line = (proc.stdout or "").strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            return {
                "available": True,
                "gpu_name": parts[0],
                "vram_total_gb": round(float(parts[1]) / 1024.0, 2),
                "vram_free_gb": round(float(parts[2]) / 1024.0, 2),
                "driver_version": parts[3],
            }
    except Exception:
        pass
    return {
        "available": False,
        "gpu_name": None,
        "vram_total_gb": 0.0,
        "vram_free_gb": 0.0,
        "driver_version": None,
    }


def get_capabilities() -> dict:
    """Report what the current environment can actually do — never fake it."""
    ffmpeg = _resolve_ffmpeg()
    colmap = shutil.which(settings.colmap_path) or shutil.which("colmap")
    blender = shutil.which(settings.blender_path) or shutil.which("blender")
    ns_train = shutil.which(settings.ns_train_path) or shutil.which("ns-train")
    ns_render = shutil.which(settings.ns_render_path) or shutil.which("ns-render")
    try:
        import torch

        cuda = bool(torch.cuda.is_available())
        gpu_name = torch.cuda.get_device_name(0) if cuda else None
        vram_gb = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2) if cuda else 0
    except Exception:
        cuda = False
        gpu_name = None
        vram_gb = 0

    gpu_hw = _probe_nvidia_smi()
    try:
        storage_dir = Path(settings.storage_root)
        storage_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(storage_dir)
        disk_info = {
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
        }
    except Exception:
        disk_info = {"total_gb": 0.0, "free_gb": 0.0}

    reconstruct_available = bool(colmap)
    render_available = bool(ns_render) and bool(cuda)
    reasons: list[str] = []
    if not colmap:
        reasons.append("COLMAP is required for camera reconstruction.")
    if not ns_render:
        reasons.append("ns-render (Nerfstudio, 3DGS) is required to render novel views.")
    if not cuda:
        reasons.append("A CUDA GPU is required for 3DGS training/rendering.")
    geometry_available = reconstruct_available and render_available

    effective_vram = vram_gb or gpu_hw.get("vram_total_gb", 0.0)
    wan_weights_dir = Path(settings.models_root) / settings.wan_model_id
    wan_weights_ready = wan_weights_dir.exists() and any(wan_weights_dir.iterdir()) if wan_weights_dir.exists() else False

    return {
        "ffmpeg": {"available": bool(ffmpeg), "path": ffmpeg},
        "colmap": {"available": bool(colmap), "path": colmap},
        "blender": {
            "available": bool(blender),
            "path": blender,
            "script_export_available": True,
        },
        "nerfstudio": {"available": bool(ns_train and ns_render), "train_path": ns_train, "render_path": ns_render},
        "cuda": {"available": cuda, "gpu_name": gpu_name, "vram_gb": vram_gb},
        "gpu_hardware": gpu_hw,
        "disk": disk_info,
        "geometry": {
            "available": geometry_available,
            "reconstruct_available": reconstruct_available,
            "render_available": render_available,
            "reason": None if geometry_available else " ".join(reasons),
            "reconstruct_reason": None if reconstruct_available else "Geometry reconstruction requires COLMAP.",
            "render_reason": None if render_available else "Novel-view rendering requires Nerfstudio (ns-render) on a CUDA GPU.",
        },
        "ai_modules": {
            "dust3r": {
                "enabled": settings.dust3r_enabled and settings.allow_non_commercial_models,
                "available": bool(settings.dust3r_enabled and settings.allow_non_commercial_models and cuda),
                "license": "CC BY-NC-SA 4.0 (Non-commercial research only)",
                "commercial_allowed": False,
                "reason": (
                    "Ready"
                    if (settings.dust3r_enabled and settings.allow_non_commercial_models and cuda)
                    else "Disabled by default (CC BY-NC-SA 4.0 non-commercial license; set CINEVIDEO_DUST3R_ENABLED=true and CINEVIDEO_ALLOW_NON_COMMERCIAL_MODELS=true)"
                ),
            },
            "moverse": {
                "enabled": settings.moverse_enabled,
                "available": bool(settings.moverse_enabled),
                "endpoint": settings.moverse_endpoint,
                "license": "Apache-2.0 / Research",
                "reason": "Ready" if settings.moverse_enabled else "Optional AI camera trajectory planner disabled by default",
            },
            "wan2_2": {
                "enabled": settings.wan_enabled,
                "available": bool(settings.wan_enabled and effective_vram >= 12.0 and wan_weights_ready),
                "model_id": settings.wan_model_id,
                "weights_present": wan_weights_ready,
                "vram_detected_gb": effective_vram,
                "min_vram_gb": 16.0,
                "license": "Apache-2.0",
                "reason": (
                    "Ready"
                    if (settings.wan_enabled and effective_vram >= 12.0 and wan_weights_ready)
                    else "Optional Wan2.2-TI2V-5B enhancement disabled or model weights not downloaded under models_root"
                ),
            },
        },
        "fallback_2_5d_lite": {"available": bool(ffmpeg)},
    }


