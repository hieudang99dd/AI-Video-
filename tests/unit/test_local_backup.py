"""P00 verifies that a local SQLite + assets snapshot can be restored and detects tampering."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.local_backup import restore_sqlite, snapshot_sqlite, verify_snapshot


def test_snapshot_restore_and_manifest(tmp_path: Path):
    db = tmp_path / "source.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT)")
        con.execute("INSERT INTO projects (name) VALUES ('Cau vuot')")
    storage = tmp_path / "files"
    storage.mkdir()
    (storage / "drawings").mkdir()
    (storage / "drawings" / "road.png").write_bytes(b"immutable-test-artifact")
    manifest_path = snapshot_sqlite(db, storage, tmp_path / "backup")
    assert manifest_path.is_file()
    report = verify_snapshot(tmp_path / "backup")
    assert report["format_version"] == 1
    assert len(report["storage"]) == 1

    newdb = tmp_path / "restored" / "project.db"
    newstorage = tmp_path / "restored" / "assets"
    restore_sqlite(tmp_path / "backup", newdb, newstorage)
    with sqlite3.connect(newdb) as con:
        assert con.execute("SELECT name FROM projects").fetchone()[0] == "Cau vuot"
    assert (newstorage / "drawings" / "road.png").read_bytes() == b"immutable-test-artifact"
    with pytest.raises(FileExistsError):
        restore_sqlite(tmp_path / "backup", newdb, newstorage)


def test_snapshot_rejects_tampered_file(tmp_path: Path):
    db = tmp_path / "source.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE demo (id INTEGER)")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "a.txt").write_text("original", encoding="utf-8")
    snap = tmp_path / "snap"
    snapshot_sqlite(db, assets, snap)
    (snap / "storage" / "a.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_snapshot(snap)


def test_snapshot_refuses_existing_dest_and_symlinks(tmp_path: Path):
    db = tmp_path / "db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE demo (id INTEGER)")
    s = tmp_path / "s"
    s.mkdir()
    snapshot_sqlite(db, s, tmp_path / "out")
    with pytest.raises(FileExistsError):
        snapshot_sqlite(db, s, tmp_path / "out")
