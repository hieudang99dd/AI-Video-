from __future__ import annotations

from unittest.mock import MagicMock, patch
from app.services.capabilities import get_capabilities


def test_capabilities_cpu_only_environment():
    with patch("shutil.which") as mock_which, patch.dict("sys.modules", {"torch": None}):
        mock_which.side_effect = lambda cmd: "/usr/bin/ffmpeg" if cmd == "ffmpeg" else None
        caps = get_capabilities()

        assert caps["ffmpeg"]["available"] is True
        assert caps["colmap"]["available"] is False
        assert caps["nerfstudio"]["available"] is False
        assert caps["nerfstudio"]["train_available"] is False
        assert caps["nerfstudio"]["render_available"] is False
        assert caps["cuda"]["available"] is False
        assert caps["geometry"]["available"] is False
        assert caps["geometry"]["reconstruct_available"] is False
        assert caps["geometry"]["train_available"] is False
        assert caps["geometry"]["render_available"] is False
        assert "COLMAP is required" in caps["geometry"]["reason"]
        assert caps["fallback_2_5d_lite"]["available"] is True


def test_capabilities_colmap_only_environment():
    with patch("shutil.which") as mock_which, patch.dict("sys.modules", {"torch": None}):
        mock_which.side_effect = lambda cmd: "/usr/bin/colmap" if cmd == "colmap" else None
        caps = get_capabilities()

        assert caps["colmap"]["available"] is True
        assert caps["geometry"]["reconstruct_available"] is True
        assert caps["geometry"]["train_available"] is False
        assert caps["geometry"]["render_available"] is False
        assert caps["geometry"]["available"] is False
        assert "CUDA" in caps["geometry"]["reason"]


def test_capabilities_full_gpu_environment():
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA RTX 4090"
    prop = MagicMock()
    prop.total_memory = 24 * (1024**3)
    mock_torch.cuda.get_device_properties.return_value = prop

    with patch("shutil.which") as mock_which, patch.dict("sys.modules", {"torch": mock_torch}):
        mock_which.return_value = "/usr/local/bin/binary"
        caps = get_capabilities()

        assert caps["ffmpeg"]["available"] is True
        assert caps["colmap"]["available"] is True
        assert caps["cuda"]["available"] is True
        assert caps["cuda"]["gpu_name"] == "NVIDIA RTX 4090"
        assert caps["cuda"]["vram_gb"] == 24.0
        assert caps["nerfstudio"]["train_available"] is True
        assert caps["nerfstudio"]["render_available"] is True
        assert caps["geometry"]["reconstruct_available"] is True
        assert caps["geometry"]["train_available"] is True
        assert caps["geometry"]["render_available"] is True
        assert caps["geometry"]["available"] is True
        assert caps["geometry"]["reason"] is None
