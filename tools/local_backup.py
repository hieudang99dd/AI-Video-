"""Local SQLite + project-storage snapshot/restore for P00 acceptance.

This tool does not support live PostgreSQL. Use pg_dump/pg_restore plus a
versioned storage backup for production. It NEVER auto-overwrites originals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for part in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _files(storage: Path):
    if storage.exists():
        for path in sorted(storage.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in snapshot storage: {path}")
            if path.is_file():
                yield path.relative_to(storage), path


def snapshot_sqlite(database: Path, storage: Path, destination: Path) -> Path:
    database, storage, destination = map(Path, (database, storage, destination))
    if not database.is_file():
        raise FileNotFoundError(f"SQLite file not found: {database}")
    if destination.exists():
        raise FileExistsError(f"Snapshot target already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=destination.parent))
    try:
        db_copy = staging / "database.sqlite"
        source_conn = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
        try:
            with sqlite3.connect(db_copy) as backup_conn:
                source_conn.backup(backup_conn)
        finally:
            source_conn.close()
        with sqlite3.connect(db_copy) as verify_conn:
            integrity = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(f"Invalid SQLite snapshot: {integrity}")
        storage_copy = staging / "storage"
        storage_copy.mkdir()
        manifest = {
            "format_version": 1,
            "database": {"path": "database.sqlite", "sha256": _sha256(db_copy)},
            "storage": [],
        }
        for relative, source in _files(storage):
            target = storage_copy / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest["storage"].append({
                "path": relative.as_posix(),
                "size": target.stat().st_size,
                "sha256": _sha256(target),
            })
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        os.replace(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return destination / "manifest.json"


def _checked_relative(value: str) -> Path:
    rel = Path(value)
    if rel.is_absolute() or not value or ".." in rel.parts or rel == Path("."):
        raise ValueError(f"Invalid path in snapshot manifest: {value!r}")
    return rel


def verify_snapshot(snapshot: Path) -> dict:
    snapshot = Path(snapshot)
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1:
        raise ValueError("Unsupported snapshot format")
    db_path = snapshot / _checked_relative(manifest["database"]["path"])
    if not db_path.is_file() or _sha256(db_path) != manifest["database"]["sha256"]:
        raise ValueError("Database checksum mismatch")
    for record in manifest["storage"]:
        source = snapshot / "storage" / _checked_relative(record["path"])
        if not source.is_file() or source.is_symlink() or _sha256(source) != record["sha256"]:
            raise ValueError(f"Storage checksum mismatch: {record['path']}")
        if source.stat().st_size != record["size"]:
            raise ValueError(f"Storage size mismatch: {record['path']}")
    # Unexpected files are not allowed; manifests must enumerate the complete snapshot.
    enumerated = {str(_checked_relative(x["path"])) for x in manifest["storage"]}
    actual = {str(rel) for rel, _ in _files(snapshot / "storage")}
    if enumerated != actual:
        raise ValueError("Snapshot contains unexpected or missing storage files")
    return manifest


def restore_sqlite(snapshot: Path, database: Path, storage: Path) -> None:
    """Restore into new/empty destinations; never overwrite existing user data."""
    snapshot, database, storage = map(Path, (snapshot, database, storage))
    verify_snapshot(snapshot)
    if database.exists() or storage.exists():
        raise FileExistsError("Restore destinations already exist; choose empty paths")
    database.parent.mkdir(parents=True, exist_ok=True)
    storage.parent.mkdir(parents=True, exist_ok=True)
    # Snapshot already verified; use temp file and atomic publish on the same volume.
    with tempfile.NamedTemporaryFile(prefix=".restore-", dir=database.parent, delete=False) as fh:
        temp_db = Path(fh.name)
    try:
        shutil.copy2(snapshot / "database.sqlite", temp_db)
        os.replace(temp_db, database)
        shutil.copytree(snapshot / "storage", storage, symlinks=False)
    except Exception:
        temp_db.unlink(missing_ok=True)
        if storage.exists():
            shutil.rmtree(storage)
        if database.exists():
            database.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Local-only SQLite and project files snapshot / restore")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("snapshot", help="Create a new checksum-verified local backup")
    create.add_argument("--database", type=Path, required=True)
    create.add_argument("--storage", type=Path, required=True)
    create.add_argument("--out", type=Path, required=True)
    restore = sub.add_parser("restore", help="Restore to brand new paths after checksum verification")
    restore.add_argument("--snapshot", type=Path, required=True)
    restore.add_argument("--database", type=Path, required=True)
    restore.add_argument("--storage", type=Path, required=True)
    check = sub.add_parser("verify", help="Verify snapshot checksums")
    check.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "snapshot":
        print(snapshot_sqlite(args.database, args.storage, args.out))
    elif args.command == "restore":
        restore_sqlite(args.snapshot, args.database, args.storage)
        print("Local restore verified and completed.")
    else:
        print(json.dumps(verify_snapshot(args.snapshot), indent=2))


if __name__ == "__main__":
    main()
