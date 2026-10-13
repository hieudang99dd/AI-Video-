from __future__ import annotations

from enum import Enum
import hashlib
import logging
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class PipelineState(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    RECONSTRUCTING = "RECONSTRUCTING"
    CAMERA_PLANNING = "CAMERA_PLANNING"
    RENDERING = "RENDERING"
    AI_ENHANCEMENT = "AI_ENHANCEMENT"
    COMPOSING = "COMPOSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PipelineState.CREATED.value: {
        PipelineState.VALIDATING.value,
        PipelineState.RECONSTRUCTING.value,
        PipelineState.CAMERA_PLANNING.value,
        PipelineState.RENDERING.value,
        PipelineState.COMPOSING.value,
        PipelineState.FAILED.value,
        PipelineState.CANCELLED.value,
    },
    PipelineState.VALIDATING.value: {
        PipelineState.RECONSTRUCTING.value,
        PipelineState.CAMERA_PLANNING.value,
        PipelineState.RENDERING.value,
        PipelineState.COMPOSING.value,
        PipelineState.COMPLETED.value,
        PipelineState.FAILED.value,
        PipelineState.CANCELLED.value,
    },
    PipelineState.RECONSTRUCTING.value: {
        PipelineState.CAMERA_PLANNING.value,
        PipelineState.RENDERING.value,
        PipelineState.COMPLETED.value,
        PipelineState.FAILED.value,
        PipelineState.CANCELLED.value,
    },
    PipelineState.CAMERA_PLANNING.value: {
        PipelineState.RENDERING.value,
        PipelineState.AI_ENHANCEMENT.value,
        PipelineState.COMPOSING.value,
        PipelineState.COMPLETED.value,
        PipelineState.FAILED.value,
        PipelineState.CANCELLED.value,
    },
    PipelineState.RENDERING.value: {
        PipelineState.AI_ENHANCEMENT.value,
        PipelineState.COMPOSING.value,
        PipelineState.COMPLETED.value,
        PipelineState.FAILED.value,
        PipelineState.CANCELLED.value,
    },
    PipelineState.AI_ENHANCEMENT.value: {
        PipelineState.COMPOSING.value,
        PipelineState.COMPLETED.value,
        PipelineState.FAILED.value,
        PipelineState.CANCELLED.value,
    },
    PipelineState.COMPOSING.value: {
        PipelineState.COMPLETED.value,
        PipelineState.FAILED.value,
        PipelineState.CANCELLED.value,
    },
    PipelineState.COMPLETED.value: {
        PipelineState.VALIDATING.value,
        PipelineState.RECONSTRUCTING.value,
        PipelineState.CAMERA_PLANNING.value,
        PipelineState.RENDERING.value,
        PipelineState.AI_ENHANCEMENT.value,
        PipelineState.COMPOSING.value,
    },
    PipelineState.FAILED.value: {
        PipelineState.CREATED.value,
        PipelineState.VALIDATING.value,
        PipelineState.RECONSTRUCTING.value,
        PipelineState.CAMERA_PLANNING.value,
        PipelineState.RENDERING.value,
        PipelineState.COMPOSING.value,
    },
    PipelineState.CANCELLED.value: {
        PipelineState.CREATED.value,
        PipelineState.VALIDATING.value,
        PipelineState.RENDERING.value,
        PipelineState.COMPOSING.value,
    },
}

_SECRET_PATTERNS = (
    re.compile(r"(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*([^\s,;\"']+)", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
)


def redact_secrets(text: str | None) -> str:
    """Redact API keys, tokens, or secrets before writing to logs or job error fields."""
    if not text:
        return ""
    cleaned = str(text)
    cleaned = _SECRET_PATTERNS[0].sub(r"\1=[REDACTED]", cleaned)
    cleaned = _SECRET_PATTERNS[1].sub("Bearer [REDACTED]", cleaned)
    return cleaned


def validate_state_transition(current_state: str, next_state: str) -> bool:
    """Check whether transitioning from ``current_state`` to ``next_state`` is valid."""
    if current_state == next_state:
        return True
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    return next_state in allowed


def transition_job_state(job: Any, next_step: PipelineState | str, message: str | None = None) -> None:
    """Advance a RenderJob's ``state_machine_step`` with provenance logging."""
    step_val = next_step.value if isinstance(next_step, PipelineState) else str(next_step)
    current = getattr(job, "state_machine_step", PipelineState.CREATED.value) or PipelineState.CREATED.value
    if not validate_state_transition(current, step_val):
        logger.warning("Forcing non-standard state transition %s -> %s for job %s", current, step_val, getattr(job, "id", "?"))
    job.state_machine_step = step_val
    prov = dict(job.provenance or {})
    history = list(prov.get("state_history") or [])
    entry = {"step": step_val, "timestamp": time.time()}
    if message:
        entry["message"] = redact_secrets(message)
    history.append(entry)
    prov["state_history"] = history
    if message:
        prov["last_message"] = redact_secrets(message)
    job.provenance = prov


def compute_job_dedup_key(project_id: str, shot_id: str | None, job_type: str, width: int, height: int, mode: str) -> str:
    raw = f"{project_id}:{shot_id or 'all'}:{job_type}:{width}x{height}:{mode}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def validate_upload_safety(filename: str, content_size_bytes: int | None = None, current_project_assets: int = 0) -> str:
    """Enforce upload security: path traversal prevention, extension whitelist, size & count limits."""
    if not filename or "\x00" in filename:
        raise ValueError("Invalid filename")
    clean = Path(filename).name
    if ".." in filename or "/" in filename or "\\" in filename:
        # Ensure we strip any directory components and reject traversal attempts if pure dots
        if clean in {".", ".."}:
            raise ValueError("Path traversal detected in filename")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", clean)[:180]
    suffix = Path(safe).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("Unsupported file extension; allowed: .jpg, .jpeg, .png, .webp")
    max_bytes = int(settings.max_upload_size_mb * 1024 * 1024)
    if content_size_bytes is not None and content_size_bytes > max_bytes:
        raise ValueError(f"File size ({content_size_bytes} bytes) exceeds limit of {settings.max_upload_size_mb} MB")
    if current_project_assets >= settings.max_assets_per_project:
        raise ValueError(f"Project reached maximum allowed assets ({settings.max_assets_per_project})")
    return safe


def cleanup_expired_temp_dirs(max_age_sec: int = 3600) -> int:
    """Clean up orphaned temporary directories created by cinevideo-* older than max_age_sec."""
    tmp_root = Path(tempfile.gettempdir())
    removed = 0
    now_ts = time.time()
    for p in tmp_root.glob("cinevideo-*"):
        try:
            if p.is_dir() and (now_ts - p.stat().st_mtime) > max_age_sec:
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
        except Exception:
            pass
    return removed


def dispatch_job_background(job_id: str) -> None:
    """Run ``render_worker.process(job_id)`` in a background daemon thread when enabled."""
    if not settings.enable_background_worker:
        return

    def _runner():
        try:
            from app.workers.render_worker import process

            process(job_id)
        except Exception as exc:
            logger.error("Background job %s failed: %s", job_id, redact_secrets(str(exc)))

    t = threading.Thread(target=_runner, name=f"cinevideo-job-{job_id[:8]}", daemon=True)
    t.start()
