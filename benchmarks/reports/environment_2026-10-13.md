# P00 local environment and baseline report — 2026-10-13 ICT

## Scope and source state

- Repository: `hieudang99dd/AI-Video-`
- Base: PR #3, `refactor/p00-p01-truthfulness-foundation@130f42b239f33c09e00fe9e87cf1810632017c7e`
- Local work branch: `refactor/p00-local-verification`
- Rollback source: remote branch `backup/pre-refactor-20261013` at `a009d19355d48c076e3494fdec1134ef2b082777`
- Original checkout was left unchanged with its ten pre-existing blank-line-only modifications.
- PR #3 was queried through the GitHub API: open, draft, mergeable, not merged.

## Work items and result

| ID | Evidence / change | Result | Remaining dependency |
|---|---|---|---|
| P00-ENV | Native tool and hardware inventory | Completed | Node, Docker, system FFmpeg/ffprobe, Blender, COLMAP and Nerfstudio are absent |
| P00-TEST | Python regression suite on PR #3 head | `148 passed, 3 warnings` | Web and Docker cannot run locally without their runtimes |
| P00-BACKUP-WIN | Close SQLite handles before atomic directory publish | Completed; Windows regression passes | Real deployment DB/object storage unavailable |
| P00-BACKUP-CLI | `snapshot` → `verify` → `restore` on representative SQLite/storage | Completed; restored DB row and asset SHA-256 match | This is representative data, not deployment recovery evidence |
| P00-CPU-MP4 | Source image → safe motion → H.264 MP4 | Completed; full decode succeeds | `ffprobe` unavailable; real Civil 3D/InfraWorks input unavailable |
| BUG-001-PAGES | Prevent fake AI/QC values in both `index.html` and deployed `docs/index.html` | Completed with regression covering both entrypoints | Real AI output/QC remains unavailable |

## Environment

| Component | Observed state |
|---|---|
| OS | Microsoft Windows 11 Pro 64-bit, build `10.0.26100`; native Windows, WSL not installed |
| Python | `3.12.10`; isolated `.venv`; pip `25.0.1` |
| Git | `2.55.0.windows.5` |
| GPU hardware | NVIDIA GeForce RTX 5070 Ti, 16,303 MiB; driver `576.88`; NVIDIA-SMI CUDA compatibility `12.9` |
| GPU software | PyTorch not installed; CUDA inference not verified |
| Disk | C: 303.39 GiB free at inspection time |
| FFmpeg | No system command. `imageio-ffmpeg` binary `7.1` works inside the Python environment |
| ffprobe | Missing; metadata was inspected with FFmpeg and OpenCV, so the explicit ffprobe gate is `NOT_RUN` |
| Node / npm | Missing |
| Docker / Compose | Missing |
| Blender | Missing |
| COLMAP | Missing |
| Nerfstudio | `ns-train` and `ns-render` missing |

Hardware presence alone is not treated as `HARDWARE_VERIFIED`: there is no installed PyTorch/CUDA runtime, COLMAP, Blender or Nerfstudio inference path.

## Commands and test evidence

```text
PYTHONPATH=apps/api;. APP_ENV=development .venv/Scripts/python -m pytest -q --disable-warnings --maxfail=1
-> 148 passed, 3 warnings in 5.98s

.venv/Scripts/python -m pytest -q tests/unit/test_local_backup.py tests/unit/test_truthfulness_regressions.py --disable-warnings
-> 13 passed, 3 warnings in 1.05s

.venv/Scripts/python tools/local_backup.py snapshot ...
.venv/Scripts/python tools/local_backup.py verify ...
.venv/Scripts/python tools/local_backup.py restore ...
-> exit 0; restored row: Representative road project
-> source/restored asset SHA-256: 03a77a7ca4ec65870b9315ea1da1bfc842e7887747695ae6a645ce98e2fe1184
```

Local `npm run build`, Docker builds, `ffprobe`, Blender, COLMAP and Nerfstudio were `NOT_RUN` because the corresponding executables are absent. Earlier CI evidence on PR #3 remains scoped to the exact SHAs recorded in `PROJECT_STATUS.md`; it is not evidence for the uncommitted changes in this worktree.

## Real CPU artifact

- Output outside Git: `../artifacts/p00-local-20261013/single_image_5s.mp4`
- Renderer: `safe_source_motion_v1` (source pixels only; not 3D or AI)
- SHA-256: `61acccbb530d75e111b59aa028d0533490b9421aaa09d407895ce875cd6b295f`
- Size: 136,288 bytes
- FFmpeg decode: exit `0`, 121 decoded frames, no decode error
- Stream metadata: H.264 High, `yuvj420p`, 1280×720, 24 fps, duration 5.04 s, no audio
- OpenCV independent check: opened, first frame decoded, 121 frames, 1280×720, 24 fps

The current renderer reports 120 generated frames while the encoded concat stream contains 121 frames because it repeats the final concat entry to honor duration. This is recorded as evidence for later P05 duration/frame-tolerance work, not hidden as an exact-frame pass.

## Runtime flow and truthfulness inventory

```text
Next.js / legacy static Pages
  -> FastAPI routes
  -> SQLAlchemy (SQLite dev / PostgreSQL target) + local/S3-style storage
  -> Redis queue when available, otherwise DB polling
  -> render worker
       -> safe source-motion FFmpeg path: locally exercised
       -> COLMAP/Nerfstudio geometry path: code present, live tools missing
       -> Blender path: script generation present; worker execution disabled by default
       -> Wan2.2/MoVerse: unavailable/fail-closed; no live inference
  -> MP4 / manifests / QC metadata
```

Known non-live or incomplete areas include the legacy Canvas point-cloud demo, disabled default Blender execution, unverified COLMAP/Nerfstudio adapters, unavailable Wan/MoVerse workers, and media QC that still needs a real `ffprobe`/decode contract under BUG-021. Decorative randomness remains in the Canvas visualization; regression only prohibits randomness from producing QC claims.

## Gate decision and rollback

- P00 / G00: `IN_PROGRESS`, not passed.
- `BLOCKED_DEPLOYMENT_DATA`: no deployment SQLite/PostgreSQL database, object storage, or authorized Civil 3D/InfraWorks dataset was present in the repository.
- `BLOCKED_TOOLING`: local web/Docker/ffprobe/3D builds cannot be executed with the installed tools.
- Rollback: discard/revert the local branch changes; source baseline remains available on `backup/pre-refactor-20261013`. No user database or storage was modified.
- Next unpassed gate: G00 still requires real deployment backup/restore, issue/board completion, and missing local build evidence (or explicitly accepted CI evidence tied to the final commit).
