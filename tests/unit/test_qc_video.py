from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.services.process_runner import ProcessResult
from app.services.renderer import QualityControlError, qc_video_output


def test_qc_video_output_file_not_found(tmp_path: Path):
    missing = tmp_path / "missing.mp4"
    with pytest.raises(QualityControlError, match="not found"):
        qc_video_output(missing)


def test_qc_video_output_file_too_small(tmp_path: Path):
    small = tmp_path / "tiny.mp4"
    small.write_bytes(b"short" * 10)  # 50 bytes
    with pytest.raises(QualityControlError, match="too small"):
        qc_video_output(small)


def test_qc_video_output_fallback_when_ffprobe_missing(tmp_path: Path):
    valid_file = tmp_path / "sample.mp4"
    valid_file.write_bytes(b"\x00" * 2048)

    with patch("shutil.which", return_value=None):
        res = qc_video_output(valid_file, expected_duration=5.0)
        assert res["qc_passed"] is True
        assert res["file_size_bytes"] == 2048
        assert res["ffprobe_inspected"] is False


def test_qc_video_output_ffprobe_success(tmp_path: Path):
    valid_file = tmp_path / "valid.mp4"
    valid_file.write_bytes(b"\x00" * 2048)

    probe_data = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "pix_fmt": "yuv420p",
                "width": 1920,
                "height": 1080,
                "duration": "5.02",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
            },
        ],
        "format": {
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": "5.02",
        },
    }

    mock_proc = ProcessResult(
        command=("ffprobe",),
        returncode=0,
        stdout=json.dumps(probe_data),
        stderr="",
        elapsed_sec=0.1,
    )

    with patch("shutil.which", return_value="/usr/bin/ffprobe"), patch(
        "app.services.renderer.run_process", return_value=mock_proc
    ):
        res = qc_video_output(
            valid_file,
            expected_duration=5.0,
            expected_resolution=(1920, 1080),
            require_audio=True,
        )
        assert res["qc_passed"] is True
        assert res["ffprobe_inspected"] is True
        assert res["codec_name"] == "h264"
        assert res["width"] == 1920
        assert res["height"] == 1080
        assert res["video_stream_count"] == 1
        assert res["audio_stream_count"] == 1


def test_qc_video_output_resolution_mismatch(tmp_path: Path):
    valid_file = tmp_path / "mismatch.mp4"
    valid_file.write_bytes(b"\x00" * 2048)

    probe_data = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1280,
                "height": 720,
            }
        ],
        "format": {"duration": "5.0"},
    }

    mock_proc = ProcessResult(
        command=("ffprobe",),
        returncode=0,
        stdout=json.dumps(probe_data),
        stderr="",
        elapsed_sec=0.1,
    )

    with patch("shutil.which", return_value="/usr/bin/ffprobe"), patch(
        "app.services.renderer.run_process", return_value=mock_proc
    ):
        with pytest.raises(QualityControlError, match="Resolution mismatch"):
            qc_video_output(valid_file, expected_resolution=(1920, 1080))


def test_qc_video_output_missing_video_stream(tmp_path: Path):
    valid_file = tmp_path / "no_video.mp4"
    valid_file.write_bytes(b"\x00" * 2048)

    probe_data = {
        "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        "format": {"duration": "5.0"},
    }

    mock_proc = ProcessResult(
        command=("ffprobe",),
        returncode=0,
        stdout=json.dumps(probe_data),
        stderr="",
        elapsed_sec=0.1,
    )

    with patch("shutil.which", return_value="/usr/bin/ffprobe"), patch(
        "app.services.renderer.run_process", return_value=mock_proc
    ):
        with pytest.raises(QualityControlError, match="No video stream found"):
            qc_video_output(valid_file)
