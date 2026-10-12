from pathlib import Path
import shutil
import tempfile
from PIL import Image
import pytest

from app.services.renderer import render_safe_motion


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_safe_renderer_outputs_mp4():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        img = root / "a.jpg"
        Image.new("RGB", (640, 480), (120, 140, 160)).save(img)
        out = root / "out.mp4"
        meta = render_safe_motion([img], out, 0.5, 12, 320, 180, lambda *_: None, lambda: False)
        assert out.exists() and out.stat().st_size > 0
        assert meta["renderer"] == "safe_source_motion_v1"
