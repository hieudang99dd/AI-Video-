#!/usr/bin/env python3
"""
GPU Environment Startup Health Check.
Fails fast with clear messages if any required dependency is missing.
This script is run on container start to validate the environment
before accepting any job.
"""
import shutil
import subprocess
import sys


def check(name: str, cmd: list[str]) -> bool:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ok = res.returncode == 0
        status = "OK" if ok else "FAIL"
        first_line = (res.stdout + res.stderr).strip().splitlines()[0] if (res.stdout + res.stderr).strip() else "(no output)"
        print(f"  [{status}] {name}: {first_line}")
        return ok
    except FileNotFoundError:
        print(f"  [FAIL] {name}: not found")
        return False
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        return False


def check_nvidia() -> bool:
    if not shutil.which("nvidia-smi"):
        print("  [FAIL] nvidia-smi: not found — no CUDA GPU visible")
        return False
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            # Extract GPU name
            for line in res.stdout.splitlines():
                if "NVIDIA" in line or "GeForce" in line or "RTX" in line or "Tesla" in line:
                    print(f"  [OK]   nvidia-smi: {line.strip()}")
                    return True
            print(f"  [OK]   nvidia-smi: available")
            return True
        else:
            print(f"  [FAIL] nvidia-smi: returned code {res.returncode}")
            return False
    except Exception as e:
        print(f"  [FAIL] nvidia-smi: {e}")
        return False


def check_torch_cuda() -> bool:
    try:
        import torch
        cuda = torch.cuda.is_available()
        name = torch.cuda.get_device_name(0) if cuda else "none"
        status = "OK" if cuda else "WARN"
        print(f"  [{status}] torch.cuda: available={cuda}, device={name}")
        return cuda
    except Exception as e:
        print(f"  [FAIL] torch: {e}")
        return False


def main():
    print("=" * 60)
    print("GPU Environment Check")
    print("=" * 60)

    results = {}
    print("\n[GPU]")
    results["nvidia-smi"] = check_nvidia()
    results["torch-cuda"] = check_torch_cuda()

    print("\n[Core Dependencies]")
    results["colmap"] = check("colmap", ["colmap", "--help"])
    results["ffmpeg"] = check("ffmpeg", ["ffmpeg", "-version"])

    print("\n[Nerfstudio]")
    results["ns-train"] = check("ns-train", ["ns-train", "--help"])
    results["ns-render"] = check("ns-render", ["ns-render", "--help"])

    print("\n[Summary]")
    all_ok = True
    for name, ok in results.items():
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}")
        if not ok:
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("STATUS: READY — All dependencies satisfied.")
        sys.exit(0)
    else:
        missing = [k for k, v in results.items() if not v]
        print(f"STATUS: NOT READY — Missing: {', '.join(missing)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

