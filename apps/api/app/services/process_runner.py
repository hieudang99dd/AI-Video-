from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

logger = logging.getLogger(__name__)

SENSITIVE_KEYWORDS = ("password", "token", "secret", "apikey", "api_key", "credential", "auth")


class ProcessRunnerError(RuntimeError):
    """Base exception for all process runner errors."""


class ExecutableNotFoundError(ProcessRunnerError):
    """Raised when the specified executable is not found."""


class ProcessTimeoutError(ProcessRunnerError):
    """Raised when process execution exceeds the configured timeout."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "", elapsed_sec: float = 0.0) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.elapsed_sec = elapsed_sec


class ProcessCancelledError(ProcessRunnerError):
    """Raised when process execution is cancelled by request."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "", elapsed_sec: float = 0.0) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.elapsed_sec = elapsed_sec


class ProcessNonZeroExitError(ProcessRunnerError):
    """Raised when process exits with a non-zero exit code and check=True."""

    def __init__(
        self,
        command: Sequence[str],
        returncode: int,
        stdout: str = "",
        stderr: str = "",
        elapsed_sec: float = 0.0,
    ) -> None:
        cmd_str = " ".join(sanitize_command(command))
        detail = (stderr or stdout or "").strip()
        super().__init__(f"Command '{cmd_str}' exited with code {returncode}: {detail[-2000:]}")
        self.command = list(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.elapsed_sec = elapsed_sec


@dataclass(frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    elapsed_sec: float
    timed_out: bool = False
    cancelled: bool = False

    @property
    def sanitized_command(self) -> list[str]:
        return sanitize_command(self.command)


def sanitize_command(args: Sequence[str]) -> list[str]:
    """Redact passwords and secrets from command arguments before logging."""
    sanitized: list[str] = []
    redact_next = False
    for arg in args:
        if redact_next:
            sanitized.append("******")
            redact_next = False
            continue

        low = arg.lower()
        if any(low == f"-{kw}" or low == f"--{kw}" for kw in SENSITIVE_KEYWORDS):
            sanitized.append(arg)
            redact_next = True
            continue

        if "=" in arg and any(kw in low.split("=")[0] for kw in SENSITIVE_KEYWORDS):
            k, _ = arg.split("=", 1)
            sanitized.append(f"{k}=******")
            continue

        # Redact user:password@ URL patterns
        sanitized_arg = re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1******\3", arg)
        sanitized.append(sanitized_arg)

    return sanitized


def kill_process_tree(proc: subprocess.Popen, timeout_sec: float = 3.0) -> None:
    """Terminate process tree cleanly to prevent orphan processes."""
    if proc.poll() is not None:
        return

    try:
        proc.terminate()
    except OSError:
        pass

    start_wait = time.monotonic()
    while time.monotonic() - start_wait < timeout_sec:
        if proc.poll() is not None:
            return
        time.sleep(0.1)

    try:
        proc.kill()
    except OSError:
        pass


def run_process(
    args: Sequence[str],
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    timeout_sec: float | None = None,
    cancel_check: Callable[[], bool] | None = None,
    check: bool = True,
    poll_interval_sec: float = 0.1,
    max_output_chars: int = 100000,
) -> ProcessResult:
    """Run an external command using argument list with timeout, cancellation, and logging.

    Guarantees:
    - Never uses shell=True
    - Captures stdout/stderr with truncation for safety
    - Handles timeout with process termination
    - Supports cancellation polling and kills process tree
    - Raises actionable, typed exceptions
    """
    if not args:
        raise ValueError("Cannot run process with empty arguments list.")

    arg_list = [str(a) for a in args]
    sanitized = sanitize_command(arg_list)
    logger.info("Executing process: %s (cwd=%s, timeout=%s)", " ".join(sanitized), cwd, timeout_sec)

    run_env = dict(env or os.environ)
    run_env.setdefault("PYTHONUTF8", "1")
    run_env.setdefault("PYTHONIOENCODING", "utf-8")

    start_time = time.monotonic()

    try:
        proc = subprocess.Popen(
            arg_list,
            cwd=str(cwd) if cwd else None,
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise ExecutableNotFoundError(f"Executable not found: {arg_list[0]}") from exc

    timed_out = False
    cancelled = False

    while proc.poll() is None:
        elapsed = time.monotonic() - start_time
        if timeout_sec is not None and elapsed > timeout_sec:
            timed_out = True
            kill_process_tree(proc)
            break
        if cancel_check is not None and cancel_check():
            cancelled = True
            kill_process_tree(proc)
            break
        time.sleep(poll_interval_sec)

    stdout, stderr = proc.communicate()
    elapsed_total = time.monotonic() - start_time

    if stdout and len(stdout) > max_output_chars:
        stdout = stdout[-max_output_chars:]
    if stderr and len(stderr) > max_output_chars:
        stderr = stderr[-max_output_chars:]

    if timed_out:
        logger.warning("Process timed out after %.2fs: %s", elapsed_total, " ".join(sanitized))
        raise ProcessTimeoutError(
            f"Process timed out after {timeout_sec}s: {sanitized[0]}",
            stdout=stdout,
            stderr=stderr,
            elapsed_sec=elapsed_total,
        )

    if cancelled:
        logger.info("Process cancelled after %.2fs: %s", elapsed_total, " ".join(sanitized))
        raise ProcessCancelledError(
            f"Process cancelled: {sanitized[0]}",
            stdout=stdout,
            stderr=stderr,
            elapsed_sec=elapsed_total,
        )

    returncode = proc.returncode or 0
    if check and returncode != 0:
        logger.error("Process failed with returncode %d: %s", returncode, " ".join(sanitized))
        raise ProcessNonZeroExitError(
            command=arg_list,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            elapsed_sec=elapsed_total,
        )

    return ProcessResult(
        command=tuple(arg_list),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        elapsed_sec=elapsed_total,
        timed_out=False,
        cancelled=False,
    )


__all__ = [
    "ProcessRunnerError",
    "ExecutableNotFoundError",
    "ProcessTimeoutError",
    "ProcessCancelledError",
    "ProcessNonZeroExitError",
    "ProcessResult",
    "sanitize_command",
    "kill_process_tree",
    "run_process",
]
