"""Image-to-Cinematic-Video API package.

SKILL_CANONICAL.md #7 keeps shared, non-HTTP code in ``<repo>/packages``
(camera math, geometry, COLMAP repository, path validation, scene grouping).
When the API is launched with ``uvicorn --app-dir apps/api`` the repository root
is not on ``sys.path``, so add it here.  The path is resolved from this file —
never hardcoded.
"""

from __future__ import annotations

import sys
from pathlib import Path

for _candidate in Path(__file__).resolve().parents:
    if (_candidate / "packages").is_dir():
        if str(_candidate) not in sys.path:
            sys.path.append(str(_candidate))
        break

