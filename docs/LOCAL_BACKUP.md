# P00 Local backup and restore (SQLite development installations)

This utility is **not a backup of the user's live deployment**. It is a tested local workflow for SQLite databases and the local `storage_root` directory.

## Prerequisites

- Stop the application/worker before restore.
- For snapshot creation, SQLite uses its online `sqlite3.Connection.backup()` API; other app file writes may occur concurrently, so preferably quiesce workers to capture consistent storage.
- Python 3.11+ with no extra packages.
- Have sufficient free disk space for duplicate project assets.

## Snapshot

```bash
python tools/local_backup.py snapshot --database /path/to/cinevideo.db --storage /path/to/cinevideo-storage --out /safe/backups/cinevideo-snapshot-001
```

The directory contains a SQLite backup, a copy of the project storage folder, and a SHA-256 checksum manifest.

The implementation explicitly closes every SQLite connection before publishing the snapshot directory. This is required on Windows, where an open database handle prevents the final atomic directory rename.

## Verify independently

```bash
python tools/local_backup.py verify --snapshot /safe/backups/cinevideo-snapshot-001
```

## Restore only into new, empty paths

```bash
python tools/local_backup.py restore --snapshot /safe/backups/cinevideo-snapshot-001 --database /safe/restore/cinevideo.db --storage /safe/restore/cinevideo-storage
```

It **refuses to overwrite** existing data, mismatched checksums or extra snapshot files. After restore, set `DATABASE_URL` and `STORAGE_ROOT` to the restored paths, run startup tests, and compare project and asset counts.

## Production PostgreSQL warning

`DATABASE_URL=postgresql+psycopg://...` **must not** be backed up with this SQLite utility. Use a verified PostgreSQL `pg_dump`/point-in-time backup and a separate versioned backup for the project object store; perform a full restore drill before marking P00 passed.

## Known limitations

- Only captures SQLite and files under a **local** storage directory; not S3 or remote GPU checkpoints.
- Can only confirm an isolated local snapshot; it does **not** prove production recoverability.
- Directory copy is not transactional with a concurrently changing remote job. For a consistent backup pause/drain jobs and stop concurrent uploads.
- Never commit customer design images, databases, project files or secret tokens to GitHub.
