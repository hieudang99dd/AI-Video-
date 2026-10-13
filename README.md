# AI-Video — Infrastructure Image-to-Video Studio

> **Refactor in progress.** This repository has a working code foundation for project/assets/shot management and a CPU source-image video pipeline. **Do not interpret camera preset/script exports, static GitHub Pages demos, or AI adapter availability as proof of live 3D camera rendering or generative AI inference.** GPU geometry pipeline and AI video require hardware-level acceptance tests.

## Canonical delivery plan

- **[MASTER_REFACTOR_PLAN.md](MASTER_REFACTOR_PLAN.md)** — single source of truth: 30 audited issues, 12 execution phases (P00–P11), dependencies, target repo architecture, gates, acceptance datasets, licensing, rollback, and agent instructions.
- [SKILL.md](SKILL.md) — agent entrypoint linking the canonical plan.
- [PROJECT_STATUS.md](PROJECT_STATUS.md) — implementation/evidence ledger (historical claims are not fresh independent verification).
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — currently implemented architecture (may lag refactor target).
- [INSTALL.md](INSTALL.md), [GPU_SETUP.md](GPU_SETUP.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — existing installation references; commands must be revalidated under Phase 00/02.

## Present architecture (audit baseline)

- Next.js app in `apps/web`, FastAPI in `apps/api`, SQLAlchemy DB, RenderJob/worker, optional Redis and Docker Compose.
- Source-image 2D/2.5D-safe FFmpeg motion renderer and scene/timeline logic; there are unit and integration tests in `tests/`.
- Camera math/presets/trajectory JSON and script export exist; current default worker branch **does not execute Blender headless**.
- COLMAP and Nerfstudio CLI integration code exists but is **not GPU-live verified** for Civil 3D/InfraWorks datasets.
- Wan2.2/MoVerse adapter stubs **do not provide verified generative inference** in current source; do not label their outputs AI-generated without proof.
- Root `index.html` on GitHub Pages is a standalone Canvas-based frontend/demo, **not** the same as a running backend-connected 3D Studio.

## Local development (legacy commands; revalidate in P00/P02)

CPU Docker configuration under `docker-compose.yml` was part of the earlier implementation, but the repository audit found packaging/build concerns. **Do not claim the following commands are verified for current HEAD until clean builds pass.**

```bash
cp .env.example .env
docker compose up --build
```

- Next.js: http://localhost:3000
- FastAPI docs: http://localhost:8000/docs

## Agent kickoff

> Read `MASTER_REFACTOR_PLAN.md`, current Git HEAD, `PROJECT_STATUS.md`, and baseline source; start at the first unpassed phase gate. Write reproducing tests, implement the actual changes, execute available checks, attach logs/artifacts, and update status with evidence. Do not skip security/truthfulness P0 issues or fake geometry/AI readiness.

Current next step: **P00 baseline and backup → P01 security/truthfulness → P02 reproducible build**. Do not market as production-ready until gates G00–G11 have been verified as applicable.
