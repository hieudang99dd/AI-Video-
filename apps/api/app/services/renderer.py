from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.core.config import settings
from app.services.capabilities import get_capabilities
from app.services.geometry_backend import GeometryError, GeometryUnavailable, get_geometry_backend
from app.services.process_runner import run_process

from packages.geometry.camera_path import CameraPathDocument
from packages.path_validation import PathValidator

ProgressFn = Callable[[float, str], None]
CancelFn = Callable[[], bool]


class QualityControlError(ValueError):
    """Raised when an output MP4 fails quality control inspection."""


def qc_video_output(
    video_path: Path,
    expected_duration: float | None = None,
    expected_fps: int | None = None,
    expected_resolution: tuple[int, int] | None = None,
    require_audio: bool = False,
    duration_tolerance_sec: float = 1.0,
) -> dict:
    """Verify generated MP4 with file metrics and deep FFprobe inspection when available.

    Adheres to docs/KE_HOACH_HOAN_THIEN_REPO.md Section 10.3 (P0 Output QC).
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise QualityControlError(f"QC FAILED: Output video file not found at {video_path}")
    size = video_path.stat().st_size
    if size < 1024:
        raise QualityControlError(f"QC FAILED: Output video file size is too small ({size} bytes, expected > 1024)")

    ffprobe = shutil.which(settings.ffprobe_path) or shutil.which("ffprobe")
    probe_report: dict = {
        "qc_passed": True,
        "file_size_bytes": size,
        "path": str(video_path),
        "expected_duration_sec": expected_duration,
        "ffprobe_inspected": False,
    }

    if not ffprobe:
        probe_report["note"] = "FFprobe not available in host environment; basic file QC passed."
        return probe_report

    try:
        proc = run_process(
            [
                ffprobe,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(video_path.resolve()),
            ],
            timeout_sec=15.0,
        )
        data = json.loads(proc.stdout)
    except Exception as exc:
        raise QualityControlError(f"QC FAILED: FFprobe inspection error: {exc}") from exc

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams:
        raise QualityControlError(f"QC FAILED: No video stream found in {video_path}")

    v_stream = video_streams[0]
    codec_name = v_stream.get("codec_name")
    pix_fmt = v_stream.get("pix_fmt")
    width = int(v_stream.get("width", 0))
    height = int(v_stream.get("height", 0))

    actual_duration = None
    if "duration" in format_info:
        try:
            actual_duration = float(format_info["duration"])
        except (ValueError, TypeError):
            pass

    probe_report.update({
        "ffprobe_inspected": True,
        "format_name": format_info.get("format_name"),
        "codec_name": codec_name,
        "pixel_format": pix_fmt,
        "width": width,
        "height": height,
        "actual_duration_sec": actual_duration,
        "video_stream_count": len(video_streams),
        "audio_stream_count": len(audio_streams),
    })

    if expected_resolution and (width, height) != expected_resolution:
        raise QualityControlError(
            f"QC FAILED: Resolution mismatch: got {width}x{height}, expected {expected_resolution[0]}x{expected_resolution[1]}"
        )

    if expected_duration is not None and actual_duration is not None:
        if abs(actual_duration - expected_duration) > duration_tolerance_sec:
            raise QualityControlError(
                f"QC FAILED: Duration mismatch: got {actual_duration:.2f}s, expected {expected_duration:.2f}s (tolerance +/- {duration_tolerance_sec}s)"
            )

    if require_audio and not audio_streams:
        raise QualityControlError(f"QC FAILED: Required audio stream is missing in {video_path}")

    return probe_report


def _apply_text_overlay(
    img: Image.Image,
    title: str | None = None,
    subtitle: str | None = None,
) -> Image.Image:
    """Apply an elegant technical engineering caption banner over the frame."""
    if not title and not subtitle:
        return img
    draw = ImageDraw.Draw(img)
    w, h = img.size
    banner_h = max(40, int(h * 0.14))
    banner_top = h - banner_h
    # Dark banner background
    draw.rectangle([(0, banner_top), (w, h)], fill=(11, 14, 18))
    font = ImageFont.load_default()
    if title:
        draw.text((24, banner_top + 10), title.upper(), fill=(245, 247, 250), font=font)
    if subtitle:
        draw.text((24, banner_top + 28), subtitle, fill=(160, 175, 190), font=font)
    return img


class GeometryPathRejected(GeometryError):
    """The sampled camera path failed validation; render must not continue."""

    def __init__(self, reasons: Sequence[str], metrics: dict | None = None) -> None:
        self.reasons = list(reasons)
        self.metrics = dict(metrics or {})
        super().__init__("camera path rejected: " + "; ".join(self.reasons))


def _ffmpeg_path() -> str:
    caps = get_capabilities()
    ffmpeg = caps["ffmpeg"]["path"]
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for video encoding")
    return ffmpeg


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _fit_cover(img: Image.Image, width: int, height: int, scale: float, pan_x: float, pan_y: float) -> Image.Image:
    src = ImageOps.exif_transpose(img).convert("RGB")
    base_ratio = max(width / src.width, height / src.height)
    target_w = max(width, int(src.width * base_ratio * scale))
    target_h = max(height, int(src.height * base_ratio * scale))
    resized = src.resize((target_w, target_h), Image.Resampling.LANCZOS)
    max_x = max(0, target_w - width)
    max_y = max(0, target_h - height)
    left = int(max_x * max(0.0, min(1.0, pan_x)))
    top = int(max_y * max(0.0, min(1.0, pan_y)))
    return resized.crop((left, top, left + width, top + height))


def _concat_escape(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def encode_frame_sequence(
    frames: Sequence[Path],
    output: Path,
    fps: int,
    progress: ProgressFn,
    cancelled: CancelFn,
    start: float = 0.9,
    end: float = 1.0,
) -> dict:
    """Encode an ordered frame list to H.264 MP4 (yuv420p, browser-safe).

    Uses the FFmpeg ``concat`` demuxer so arbitrary frame filenames work, which
    lets the same encoder serve both the CPU fallback (JPEG frames) and the
    geometry renderer (PNG frames from ``ns-render``).
    """
    frames = [Path(f) for f in frames]
    if not frames:
        raise ValueError("no frames to encode")
    ffmpeg = _ffmpeg_path()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cinevideo-encode-") as tmp:
        listing = Path(tmp) / "frames.txt"
        with listing.open("w", encoding="utf-8") as handle:
            for frame in frames:
                handle.write(f"file '{_concat_escape(frame.resolve())}'\nduration {1.0 / float(fps):.6f}\n")
            # concat demuxer needs the last entry repeated to honour its duration
            handle.write(f"file '{_concat_escape(frames[-1].resolve())}'\n")

        if cancelled():
            raise InterruptedError("cancel requested")
        progress(start, f"Encoding MP4 ({len(frames)} frames)")
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-vsync", "cfr", "-r", str(fps),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output),
        ]
        run_process(cmd, timeout_sec=180.0, cancel_check=cancelled)

    progress(end, "Completed")
    return {"frames": len(frames), "fps": fps, "codec": "h264", "encoder": "ffmpeg_concat_v1"}


def render_safe_motion(
    image_paths: list[Path],
    output: Path,
    duration_sec: float,
    fps: int,
    width: int,
    height: int,
    progress: ProgressFn,
    cancelled: CancelFn,
    overlay_title: str | None = None,
    subtitle_text: str | None = None,
) -> dict:
    if not image_paths:
        raise ValueError("shot has no images")

    total_frames = max(2, int(duration_sec * fps))
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cinevideo-") as tmp:
        tmpdir = Path(tmp)
        images = [Image.open(p) for p in image_paths]
        try:
            n = len(images)
            for frame_idx in range(total_frames):
                if cancelled():
                    raise InterruptedError("cancel requested")
                global_t = frame_idx / max(1, total_frames - 1)
                position = global_t * n
                idx = min(n - 1, int(position))
                local_t = position - math.floor(position)
                eased = _ease(local_t)

                # Very conservative source-image motion: max 6% zoom and mild pan.
                scale = 1.0 + 0.06 * eased
                direction = -1.0 if idx % 2 else 1.0
                pan_x = 0.5 + direction * 0.12 * (eased - 0.5)
                pan_y = 0.5 + 0.06 * math.sin(global_t * math.pi)
                a = _fit_cover(images[idx], width, height, scale, pan_x, pan_y)

                # Crossfade only near the end of each image segment; no invented geometry.
                if idx < n - 1 and local_t > 0.82:
                    alpha = (local_t - 0.82) / 0.18
                    b = _fit_cover(images[idx + 1], width, height, 1.0 + 0.02 * alpha, 0.5, 0.5)
                    a = Image.blend(a, b, alpha=max(0.0, min(1.0, alpha)))

                if overlay_title or subtitle_text:
                    a = _apply_text_overlay(a, overlay_title, subtitle_text)

                a.save(tmpdir / f"frame_{frame_idx:06d}.jpg", quality=92)
                if frame_idx % max(1, fps // 2) == 0:
                    progress(0.1 + 0.75 * global_t, f"Rendering frame {frame_idx + 1}/{total_frames}")

            progress(0.88, "Encoding MP4")
            actual_frames = sorted(tmpdir.glob("frame_*.jpg"))
        finally:
            for img in images:
                img.close()
        encode = encode_frame_sequence(actual_frames, output, fps, progress, cancelled, start=0.88, end=1.0)

    qc = qc_video_output(output, duration_sec)

    return {
        "renderer": "safe_source_motion_v1",
        "frames": total_frames,
        "duration_sec": duration_sec,
        "fps": fps,
        "resolution": [width, height],
        "encoding": encode,
        "qc": qc,
        "notes": "Source-image motion only; no free-view geometry hallucination.",
    }


def concatenate_timeline(
    shot_video_paths: list[Path],
    output: Path,
    progress: ProgressFn,
    cancelled: CancelFn,
    bgm_path: Path | None = None,
) -> dict:
    """Concatenate multiple rendered shot MP4s into a single seamless project video.

    Optionally mixes background music (BGM) with soft audio ducking.
    """
    if not shot_video_paths:
        raise ValueError("No shot videos to concatenate")

    ffmpeg = _ffmpeg_path()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cinevideo-timeline-") as tmp:
        listing = Path(tmp) / "timeline.txt"
        with listing.open("w", encoding="utf-8") as handle:
            for p in shot_video_paths:
                handle.write(f"file '{_concat_escape(p.resolve())}'\n")

        if cancelled():
            raise InterruptedError("cancel requested")

        progress(0.5, f"Assembling timeline from {len(shot_video_paths)} shots")

        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(listing),
        ]

        if bgm_path and bgm_path.exists():
            cmd.extend([
                "-i", str(bgm_path.resolve()),
                "-filter_complex", "[1:a]volume=0.25[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]",
                "-map", "0:v", "-map", "[aout]",
            ])
        else:
            cmd.extend(["-c:v", "copy"])

        cmd.extend(["-movflags", "+faststart", str(output)])
        run_process(cmd, timeout_sec=300.0, cancel_check=cancelled)

    qc = qc_video_output(output)
    progress(1.0, "Timeline assembled successfully")

    return {
        "renderer": "timeline_assembly_v1",
        "shot_count": len(shot_video_paths),
        "output": str(output),
        "qc": qc,
        "bgm_applied": bool(bgm_path and bgm_path.exists()),
    }


def geometry_capability_reason() -> str | None:
    """``None`` when Geometry Mode can run here, otherwise an actionable reason."""
    caps = get_capabilities()
    if caps["geometry"]["available"]:
        return None
    return caps["geometry"]["reason"] or "Geometry Mode is unavailable in this environment."


def render_geometry_motion(
    scene_uri: str,
    camera_path: CameraPathDocument | dict,
    output: Path,
    fps: int,
    width: int,
    height: int,
    progress: ProgressFn,
    cancelled: CancelFn,
    backend=None,
    proxy=None,
    frames_dir: Path | None = None,
) -> dict:
    """Render novel views for a validated camera path and encode an MP4.

    Order matters (SKILL_CANONICAL #4.0 rule 7): sample -> validate -> render ->
    encode.  Final output is never produced before the path passes validation.

    Raises :class:`GeometryUnavailable` (missing COLMAP/3DGS/GPU) or
    :class:`GeometryPathRejected` (unsafe path) so the caller can fall back with a
    recorded reason instead of shipping a hallucinated video.
    """
    reason = geometry_capability_reason()
    if reason:
        raise GeometryUnavailable(reason)

    backend = backend or get_geometry_backend()
    document = (
        camera_path
        if isinstance(camera_path, CameraPathDocument)
        else CameraPathDocument.from_dict(camera_path)
    )
    document.validate()
    if document.fps != fps:
        raise GeometryError(f"camera path fps {document.fps} does not match job fps {fps}")
    if (document.width, document.height) != (width, height):
        raise GeometryError(
            f"camera path resolution {document.width}x{document.height} does not match job {width}x{height}"
        )

    validator = PathValidator(
        {
            "max_angular_velocity_deg_sec": settings.max_angular_velocity_deg_sec,
            "max_focal_change_ratio": settings.max_focal_change_ratio,
            "min_score": settings.min_render_score,
        }
    )
    progress(0.05, "Validating camera path")
    samples = validator.sample_path(document)
    validation = validator.validate(samples, proxy)
    if not validation.ok:
        raise GeometryPathRejected(validation.rejection_reasons, metrics=validation.metrics)

    if cancelled():
        raise InterruptedError("cancel requested")

    temp_frames = None
    if frames_dir is None:
        temp_frames = tempfile.TemporaryDirectory(prefix="cinevideo-geometry-")
        frames_dir = Path(temp_frames.name)
    try:
        progress(0.1, "Rendering novel views (3DGS)")
        rendered = backend.render_camera_path(scene_uri, document, Path(frames_dir))
        if cancelled():
            raise InterruptedError("cancel requested")
        encoding = encode_frame_sequence(
            rendered.frames, output, fps, progress, cancelled, start=0.9, end=1.0
        )
    finally:
        if temp_frames is not None:
            temp_frames.cleanup()

    return {
        "renderer": "geometry_3dgs_v1",
        "frames": encoding["frames"],
        "duration_sec": document.duration_sec,
        "fps": fps,
        "resolution": [width, height],
        "encoding": encoding,
        "geometry": rendered.metadata,
        "path_validation": {
            "ok": validation.ok,
            "score": round(validation.score, 4),
            "metrics": validation.metrics,
        },
        "notes": "Novel views rendered from the reconstructed scene; no generative fill.",
    }

