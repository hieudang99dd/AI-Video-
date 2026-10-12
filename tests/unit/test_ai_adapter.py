from pathlib import Path
import pytest
from app.services.ai_adapter import AIProviderAdapter, ai_adapter


def test_ai_adapter_is_disabled_by_default():
    adapter = AIProviderAdapter(enabled=False)
    status = adapter.is_available()
    assert status["available"] is False
    assert "disabled by default" in status["reason"]


def test_ai_adapter_generate_clip_raises_when_disabled():
    adapter = AIProviderAdapter(enabled=False)
    with pytest.raises(RuntimeError, match="Fallback to 2D_IMAGE_CAMERA"):
        adapter.generate_clip(
            image_path=Path("dummy.jpg"),
            prompt="cinematic road flyover",
            duration_sec=5.0,
            fps=30,
            output_path=Path("dummy.mp4"),
            progress_callback=lambda *_: None,
            cancel_callback=lambda: False,
        )


def test_singleton_ai_adapter_is_safe():
    status = ai_adapter.is_available()
    assert status["available"] is False

