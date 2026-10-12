from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


class LocalStorage:
    def __init__(self, root: Path | None = None):
        self.root = root or settings.storage_root
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe(self, rel: str) -> Path:
        target = (self.root / rel).resolve()
        root = self.root.resolve()
        if root not in target.parents and target != root:
            raise ValueError("invalid storage path")
        return target

    def save_stream(self, rel: str, stream: BinaryIO) -> tuple[str, str]:
        path = self._safe(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        with path.open("wb") as out:
            while chunk := stream.read(1024 * 1024):
                h.update(chunk)
                out.write(chunk)
        return f"local://{rel}", h.hexdigest()

    def resolve(self, uri: str) -> Path:
        if not uri.startswith("local://"):
            raise ValueError(f"unsupported URI: {uri}")
        return self._safe(uri[len("local://"):])

    def copy_in(self, source: Path, rel: str) -> str:
        target = self._safe(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return f"local://{rel}"


storage = LocalStorage()
