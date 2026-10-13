from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AIProviderAdapter:
    """Out-of-process adapter for optional generative AI video models (e.g. ComfyUI / Wan2.2).

    Adheres strictly to the invariant:
    - Never mandatory for basic MP4 export.
    - Disabled by default to protect technical engineering geometry.
    - Out-of-process network interface only (never links GPL code).
    - Gracefully falls back to 2D_IMAGE_CAMERA on timeout or error.
    """

    def __init__(self, endpoint_url: str = "http://localhost:8188", enabled: bool = False) -> None:
        self.endpoint_url = endpoint_url
        self.enabled = enabled

    def is_available(self) -> dict[str, Any]:
        """Check if the AI provider server is reachable and active."""
        if not self.enabled:
            return {
                "available": False,
                "reason": "AI video adapter is disabled by default in settings to preserve engineering geometry",
                "endpoint": self.endpoint_url,
            }

        # In production, this performs a lightweight GET /system_stats or /health check
        try:
            import urllib.request

            req = urllib.request.Request(f"{self.endpoint_url}/system_stats", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    return {"available": True, "reason": "ComfyUI AI Server online", "endpoint": self.endpoint_url}
        except Exception as exc:
            return {
                "available": False,
                "reason": f"Cannot connect to AI endpoint: {exc}",
                "endpoint": self.endpoint_url,
            }

        return {"available": False, "reason": "Endpoint unavailable", "endpoint": self.endpoint_url}

    def generate_clip(
        self,
        image_path: Path,
        prompt: str,
        duration_sec: float,
        fps: int,
        output_path: Path,
        progress_callback: Callable[[float, str], None],
        cancel_callback: Callable[[], bool],
    ) -> dict[str, Any]:
        """Generate a video clip using the external AI provider, with timeout and safe fallback.

        Raises:
            RuntimeError: If adapter is unavailable or processing fails and caller needs to fallback.
        """
        status = self.is_available()
        if not status["available"]:
            raise RuntimeError(f"AI Provider unavailable: {status['reason']}. Fallback to 2D_IMAGE_CAMERA.")

        if cancel_callback():
            raise InterruptedError("AI render cancelled by user")

        raise NotImplementedError("AI inference adapter is not implemented; no AI artifact was produced.")


class DUSt3RAdapter:
    """Optional multi-view stereo reconstruction fallback adapter (naver/dust3r).

    Strictly gated behind non-commercial license acknowledgement (CC BY-NC-SA 4.0).
    """

    LICENSE = "CC BY-NC-SA 4.0 (Non-Commercial Research Only)"

    def status(self) -> dict[str, Any]:
        from app.core.config import settings
        from app.services.capabilities import get_capabilities

        caps = get_capabilities()
        return caps["ai_modules"]["dust3r"]

    def check_license_and_availability(self) -> tuple[bool, str]:
        st = self.status()
        if not st["enabled"]:
            return (
                False,
                "DUSt3R is disabled by default due to CC BY-NC-SA 4.0 non-commercial license. "
                "Set CINEVIDEO_DUST3R_ENABLED=true and CINEVIDEO_ALLOW_NON_COMMERCIAL_MODELS=true for research use.",
            )
        if not st["available"]:
            return False, st["reason"]
        return True, "DUSt3R ready (non-commercial mode)"


class MoVerseAdapter:
    """Optional camera trajectory refinement adapter (Orange-3DV-Team/MoVerse)."""

    LICENSE = "Apache-2.0 / Research"

    def status(self) -> dict[str, Any]:
        from app.services.capabilities import get_capabilities

        return get_capabilities()["ai_modules"]["moverse"]


class Wan22Adapter:
    """Optional AI Video Enhancement adapter for Wan-Video/Wan2.2 (Wan2.2-TI2V-5B).

    Invariants:
    - Never auto-downloads multi-GB weights during install.
    - Checks GPU, VRAM, CUDA, and local weights before running.
    - Always keeps original 3D/plate render intact so user can compare and revert.
    - Always attaches mandatory engineering disclaimer (`AI_ENHANCED`).
    """

    LICENSE = "Apache-2.0"
    DISCLAIMER = (
        "AI_ENHANCED — Hình ảnh đã qua xử lý bởi mô hình AI (Wan2.2-TI2V-5B), "
        "chỉ phục vụ minh họa trình chiếu, không phải hồ sơ kỹ thuật gốc."
    )

    def status(self) -> dict[str, Any]:
        from app.services.capabilities import get_capabilities

        return get_capabilities()["ai_modules"]["wan2_2"]

    def enhance_render(
        self,
        source_video_path: Path,
        output_video_path: Path,
        prompt: str,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Fail closed until a real, independently verified Wan2.2 runner is installed.

        This function must never copy input to output and label it AI-generated.
        A future implementation must return evidence: model SHA, prompt, seed,
        actual command/job identifier, output checksum and inference logs.
        """
        if not source_video_path.is_file():
            raise FileNotFoundError(f"Source render not found: {source_video_path}")
        raise NotImplementedError(
            "Wan2.2 diffusion inference has not been integrated. "
            "The presence of GPU or model files is NOT proof of an inference worker."
        )


ai_adapter = AIProviderAdapter()
dust3r_adapter = DUSt3RAdapter()
moverse_adapter = MoVerseAdapter()
wan22_adapter = Wan22Adapter()


def get_all_ai_modules_status() -> dict[str, Any]:
    return {
        "comfyui_legacy": ai_adapter.is_available(),
        "dust3r": dust3r_adapter.status(),
        "moverse": moverse_adapter.status(),
        "wan2_2": wan22_adapter.status(),
    }


