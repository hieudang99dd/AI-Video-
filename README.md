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

## Khởi động trực tiếp (Không cần chạy file .bat)

Chỉ cần chạy 1 lệnh duy nhất bằng Python:

```bash
python run.py
```

Lệnh này sẽ:
- Khởi động máy chủ Web UI Studio tại `http://localhost:8000`.
- Tự động kích hoạt Render Worker chạy ngầm trong cùng tiến trình (xử lý render ngay lập tức mà không cần mở terminal thứ hai hay file `.bat`).
- Tự động mở trình duyệt web đến ứng dụng.

Hoặc mở trực tiếp file `index.html` trong bất kỳ trình duyệt web nào (Chrome, Edge) để trải nghiệm chế độ Studio Độc Lập hoàn toàn offline mà không cần khởi động bất kỳ tiến trình nào.

### Tùy chọn chạy thủ công:

```bash
# Chỉ chạy server (Worker đã được nhúng sẵn tự động):
uvicorn app.main:app --app-dir apps/api --reload
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
