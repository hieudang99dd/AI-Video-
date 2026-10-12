from __future__ import annotations

import shutil
from app.core.config import settings


def get_capabilities() -> dict:
    """Report what the current environment can actually do — never fake it.

    Conforms to docs/KE_HOACH_HOAN_THIEN_REPO.md Section 6.1.
    """
    ffmpeg = shutil.which(settings.ffmpeg_path) or shutil.which("ffmpeg")
    colmap = shutil.which(settings.colmap_path) or shutil.which("colmap")
    ns_train = shutil.which(settings.ns_train_path) or shutil.which("ns-train")
    ns_render = shutil.which(settings.ns_render_path) or shutil.which("ns-render")

    cuda = False
    gpu_name = None
    vram_gb = 0.0
    cuda_error: str | None = None

    try:
        import torch

        cuda = bool(torch.cuda.is_available())
        if cuda:
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
        else:
            cuda_error = "CUDA is not available in PyTorch on this host."
    except Exception as exc:
        cuda = False
        gpu_name = None
        vram_gb = 0.0
        cuda_error = f"PyTorch import or CUDA detection failed: {exc}"

    reconstruct_available = bool(colmap)
    train_available = bool(ns_train) and bool(cuda)
    render_available = bool(ns_render) and bool(cuda)

    reasons: list[str] = []
    if not colmap:
        reasons.append("COLMAP is required for camera reconstruction.")
    if not ns_train:
        reasons.append("ns-train (Nerfstudio, 3DGS) is required to train splatfacto models.")
    if not ns_render:
        reasons.append("ns-render (Nerfstudio, 3DGS) is required to render novel views.")
    if not cuda:
        reasons.append("A CUDA GPU is required for 3DGS training/rendering.")

    geometry_available = reconstruct_available and train_available and render_available

    return {
        "ffmpeg": {"available": bool(ffmpeg), "path": ffmpeg},
        "colmap": {"available": bool(colmap), "path": colmap},
        "nerfstudio": {
            "available": bool(ns_train and ns_render),
            "train_available": bool(ns_train),
            "render_available": bool(ns_render),
            "train_path": ns_train,
            "render_path": ns_render,
        },
        "cuda": {
            "available": cuda,
            "gpu_name": gpu_name,
            "vram_gb": vram_gb,
            "error": cuda_error,
        },
        "geometry": {
            "available": geometry_available,
            "reconstruct_available": reconstruct_available,
            "train_available": train_available,
            "render_available": render_available,
            "reason": None if geometry_available else " ".join(reasons),
            "reconstruct_reason": None if reconstruct_available else "Geometry reconstruction requires COLMAP.",
            "train_reason": None if train_available else "3DGS training requires Nerfstudio (ns-train) on a CUDA GPU.",
            "render_reason": None if render_available else "Novel-view rendering requires Nerfstudio (ns-render) on a CUDA GPU.",
        },
        "fallback_2_5d_lite": {"available": bool(ffmpeg)},
    }
