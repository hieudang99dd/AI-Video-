#!/usr/bin/env python
"""Universal Launcher for AI-Video Studio Suite.

Chay truc tiep bang:
    python run.py
Khong can phai mo file .bat rieng nua!
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add apps/api and packages to PYTHONPATH
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT))


def open_browser_delayed(url: str, delay_sec: float = 1.2):
    time.sleep(delay_sec)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    url = f"http://localhost:{port}"

    print("=" * 64)
    print("  🎬 AI-VIDEO: STUDIO BIEN TAP PHAN CANH & RENDER ENGINE")
    print("=" * 64)
    print(f"  * Giao dien Studio Suite: {url}")
    print("  * Worker xu ly video render da duoc tich hop san.")
    print("  * Trinh duyet web se tu dong mo len...")
    print("  * Nhan Ctrl+C de dung ung dung.")
    print("=" * 64, flush=True)

    # Auto-open browser in background thread
    threading.Thread(target=open_browser_delayed, args=(url, 1.2), daemon=True).start()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        app_dir=str(ROOT / "apps" / "api"),
    )


if __name__ == "__main__":
    main()
