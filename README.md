# Image-to-Cinematic-Video

Phase 0/1 vertical slice built from `SKILL_CANONICAL.md`.

## What works now

- Web UI (Next.js) for project creation, upload, analysis, shot creation and render jobs.
- FastAPI API with persistent projects/assets/shots/render jobs.
- Worker abstraction: render work never runs inside the HTTP request.
- Local dev queue works with Redis when available, otherwise the worker polls the DB.
- Image QA: dimensions, brightness, sharpness proxy.
- Safe CPU video fallback (`2.5d_lite` / transition) using source images + gentle crop/pan/zoom only.
- FFmpeg H.264 MP4 encoding.
- Capability endpoint that reports COLMAP / Geometry availability instead of faking it.
- Camera math package with easing, quaternion normalization and SLERP.
- Docker Compose for web, API, worker, PostgreSQL and Redis.

## Intentionally not faked

`Geometry Mode` (COLMAP + 3DGS) is **not pretended to work** when dependencies/GPU are absent. The API exposes capabilities and a geometry render request fails with an actionable message. This follows the canonical skill: fallback instead of hallucination.

## Quick start — Docker

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs

## Quick start — API/worker without Docker

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e './apps/api[dev]'
export DATABASE_URL=sqlite:////tmp/cinevideo.db
export STORAGE_ROOT=/tmp/cinevideo-storage
uvicorn app.main:app --app-dir apps/api --reload
```

In a second terminal:

```bash
export DATABASE_URL=sqlite:////tmp/cinevideo.db
export STORAGE_ROOT=/tmp/cinevideo-storage
python -m app.workers.render_worker --app-dir apps/api
```

For local source execution, simpler:

```bash
PYTHONPATH=apps/api python -m app.workers.render_worker
```

## Core API flow

1. `POST /api/v1/projects`
2. `POST /api/v1/projects/{project_id}/assets`
3. `POST /api/v1/projects/{project_id}/analyze`
4. `POST /api/v1/projects/{project_id}/shots`
5. `POST /api/v1/shots/{shot_id}/preview`
6. poll `GET /api/v1/render-jobs/{job_id}`
7. `GET /api/v1/render-jobs/{job_id}/download`

## Next milestone

Phase 0 geometry spike:

- integrate COLMAP/PyCOLMAP behind `GeometryBackend`;
- export registered cameras + sparse scene;
- add 3DGS backend behind the same render contract;
- validate 5-second geometry shot on the benchmark datasets before Hybrid GPU work begins.
