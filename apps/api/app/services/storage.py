from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

from app.core.config import settings


class LocalStorage:
    """Project storage with bounded streaming and atomic publishing.

    Never leave partially uploaded files under a public asset URI. Only publish
    after validation and hashing of the complete upload.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else Path(settings.storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe(self, rel: str) -> Path:
        target = (self.root / rel).resolve()
        root = self.root.resolve()
        if root not in target.parents and target != root:
            raise ValueError("invalid storage path")
        return target

    def save_stream(
        self,
        rel: str,
        stream: BinaryIO,
        max_bytes: int | None = None,
        verify_image: bool = False,
    ) -> tuple[str, str]:
        path = self._safe(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        limit = max_bytes
        if limit is not None and limit <= 0:
            raise ValueError("Upload size limit must be greater than zero.")

        h = hashlib.sha256()
        total = 0
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".upload-", suffix=".tmp", dir=path.parent, delete=False
            ) as out:
                temp_path = Path(out.name)
                while chunk := stream.read(1024 * 1024):
                    total += len(chunk)
                    if limit is not None and total > limit:
                        raise ValueError("UPLOAD_TOO_LARGE")
                    h.update(chunk)
                    out.write(chunk)

            if total == 0:
                raise ValueError("EMPTY_UPLOAD")

            if verify_image:
                formats = {
                    ".jpg": "JPEG",
                    ".jpeg": "JPEG",
                    ".png": "PNG",
                    ".webp": "WEBP",
                }
                expected = formats.get(path.suffix.lower())
                if expected is None:
                    raise ValueError("UNSUPPORTED_IMAGE_FORMAT")
                try:
                    with Image.open(temp_path) as image:
                        if image.format != expected:
                            raise ValueError("IMAGE_FORMAT_MISMATCH")
                        if image.width < 1 or image.height < 1:
                            raise ValueError("INVALID_IMAGE_DIMENSIONS")
                        if image.width * image.height > settings.max_image_pixels:
                            raise ValueError("IMAGE_PIXEL_LIMIT_EXCEEDED")
                        image.verify()
                except (UnidentifiedImageError, OSError) as exc:
                    raise ValueError("INVALID_IMAGE_DATA") from exc

            os.replace(temp_path, path)
            return f"local://{rel}", h.hexdigest()
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

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
