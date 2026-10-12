from __future__ import annotations

import sys
import pytest
from app.services.process_runner import (
    ExecutableNotFoundError,
    ProcessCancelledError,
    ProcessNonZeroExitError,
    ProcessTimeoutError,
    run_process,
    sanitize_command,
)


def test_sanitize_command_redacts_credentials():
    cmd = ["ffmpeg", "-password", "supersecret123", "-i", "http://user:token@example.com", "token=hidden999"]
    sanitized = sanitize_command(cmd)
    assert "supersecret123" not in sanitized
    assert "******" in sanitized
    assert "token=******" in sanitized


def test_run_process_success():
    res = run_process([sys.executable, "-c", "print('hello from process runner')"])
    assert res.returncode == 0
    assert "hello from process runner" in res.stdout
    assert not res.timed_out
    assert not res.cancelled


def test_run_process_arguments_with_spaces():
    text = "text with spaces and unicode: Tiếng Việt"
    res = run_process([sys.executable, "-c", "import sys; print(sys.argv[1])", text])
    assert res.returncode == 0
    assert text in res.stdout


def test_run_process_missing_binary():
    with pytest.raises(ExecutableNotFoundError) as exc_info:
        run_process(["non_existent_binary_xyz_123456"])
    assert "non_existent_binary_xyz_123456" in str(exc_info.value)


def test_run_process_non_zero_exit():
    with pytest.raises(ProcessNonZeroExitError) as exc_info:
        run_process([sys.executable, "-c", "import sys; sys.stderr.write('fatal failure\\n'); sys.exit(42)"])
    assert exc_info.value.returncode == 42
    assert "fatal failure" in exc_info.value.stderr


def test_run_process_non_zero_exit_no_check():
    res = run_process([sys.executable, "-c", "import sys; sys.exit(7)"], check=False)
    assert res.returncode == 7


def test_run_process_timeout():
    with pytest.raises(ProcessTimeoutError) as exc_info:
        run_process([sys.executable, "-c", "import time; time.sleep(5)"], timeout_sec=0.3)
    assert "timed out" in str(exc_info.value).lower()
    assert exc_info.value.elapsed_sec >= 0.2


def test_run_process_cancellation():
    cancelled_flag = False

    def check_cancel() -> bool:
        return cancelled_flag

    # Trigger cancel after short delay
    import threading

    def trigger():
        import time
        time.sleep(0.15)
        nonlocal cancelled_flag
        cancelled_flag = True

    t = threading.Thread(target=trigger)
    t.start()

    with pytest.raises(ProcessCancelledError):
        run_process([sys.executable, "-c", "import time; time.sleep(5)"], cancel_check=check_cancel)
    t.join()
