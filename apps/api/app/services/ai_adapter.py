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

        progress_callback(0.2, "Calling AI video service...")
        # Out-of-process workflow dispatch placeholder
        # Returns metadata regarding the generation
        return {
            "provider": "comfyui_wan2.2",
            "model": "Wan2.2-14B-FunControl",
            "duration_sec": duration_sec,
            "fps": fps,
            "fidelity_disclaimer": "AI generated visualization; not an authoritative engineering geometry source.",
        }


ai_adapter = AIProviderAdapter()
