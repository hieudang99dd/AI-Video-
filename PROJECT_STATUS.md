# AI-Video — evidence-based project status

**Canonical specification:** [MASTER_REFACTOR_PLAN.md](MASTER_REFACTOR_PLAN.md). This file is **not** a second roadmap.

**Baseline inspected:** `main` @ `87cc55241198d3654246ff3943a4c99c8b303063` (2026-10-13 ICT). Source review confirmed multiple modules exist, but **this documentation update did not run a fresh local test suite, GPU benchmark, clean Docker build, or live 3D inference.** Prior claims that 121 tests passed refer to earlier project reporting only and **are not independent proof for the current baseline**.

## Current phase

**P00 — IN_PROGRESS** (baseline source inspected; backup branch created; new CPU CI workflow and regression fixes prepared on a feature branch; CI result/DB restore still required). **G00 not passed.** P01 fixes are staged for review but **G01 not passed**.

## Phase tracker (complete the evidence before any GATE_PASSED)

| Phase | State | Evidence / PR | Critical blocker |
|---|---|---|---|
| P00 | IN_PROGRESS | [#1](https://github.com/hieudang99dd/AI-Video-/issues/1), backup branch, CI workflow on feature branch | CI results and DB/storage backup+restore pending |
| P01 | IN_PROGRESS | [#2](https://github.com/hieudang99dd/AI-Video-/issues/2), P0 code fixes staged on feature branch | per-user/tenant auth and live AI/QC verification still missing |
| P02 | NOT_STARTED | — | Docker packaging and GPU container validation |
| P03 | NOT_STARTED | — | atomic jobs, dedup, migration |
| P04 | NOT_STARTED | — | benchmarked ingestion/grouping |
| P05 | NOT_STARTED | — | independently verified FFmpeg CPU e2e |
| P06 | NOT_STARTED | — | one camera path across renderers |
| P07 | NOT_STARTED | — | live COLMAP/3DGS/Blender GPU test |
| P08 | NOT_STARTED | — | consolidated API-connected Studio |
| P09 | NOT_STARTED | — | real Wan inference/AI QC/license gate |
| P10 | NOT_STARTED | — | golden tests and reliability benchmarks |
| P11 | NOT_STARTED | — | production isolation, operations and rollback |

Valid values: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `GATE_PASSED`, `REOPENED`.

## Confirmed from static code review (not live certification)

- Project/asset/scene/shot/RenderJob models and FastAPI routes are implemented.
- Camera trajectory, quaternion interpolation, COLMAP repository parser, geometry CLI adapters, FFmpeg compositor and test files exist.
- Current safe source-image render path uses pan/zoom/crossfade; novel-view 3D is **not yet hardware-verified**.
- Current Blender worker exports script but uses `execute_if_available=False` in default render flow.
- Current Wan2.2 adapter copies source video; no verified diffusion inference.
- Current public Pages QC uses random metrics; backend AI QC compares source images against themselves in relevant route. **Both must be fixed before enabling any pass labeling.**
- Backend currently lacks project-scoped authentication/authorization.

## Immediate execution checklist

- [x] P00-01 create `backup/pre-refactor-20261013` branch from baseline commit `a009d193`\n- [ ] P00-01b backup and **restore test** for deployment DB/storage (cannot access from GitHub only)
- [x] P00-02a add CI workflow on feature branch for `pytest`, Next build and API Docker clean build\n- [ ] P00-02b check CI logs; do not claim tests passed before execution
- [x] P00-03 inspect code tree + core modules at baseline\n- [ ] P00-03b inventory deployment datasets and backup artifacts
- [x] P00-04 create [P00 issue #1](https://github.com/hieudang99dd/AI-Video-/issues/1) and [P01 issue #2](https://github.com/hieudang99dd/AI-Video-/issues/2)\n- [ ] P00-04b create/assign remaining issue tickets for P02–P11
- [x] P00-05 open controlled branch `refactor/p00-p01-truthfulness-foundation`; never fake completed

## Update protocol

For each merged PR add: date, HEAD SHA, issue IDs, phase, tests with exact commands and results, source dataset/version, output artifacts/ffprobe, GPU/VRAM if used, blockers, reviewer, fallback/rollback procedure. The phase gate may change to `GATE_PASSED` only when every criterion in `MASTER_REFACTOR_PLAN.md` is demonstrated.

## P00/P01 engineering changes staged (branch only — 2026-10-13)
- Source baseline: `main@a009d19355d48c076e3494fdec1134ef2b082777`.
- Rollback source: `backup/pre-refactor-20261013` (GitHub branch, **not a DB backup**).
- BUG-001: GitHub Pages QC scores now show NOT_RUN; static AI approval cannot be accepted.
- BUG-003/004: Wan2.2 copy-to-video adapter replaced by explicit NotImplementedError; AI endpoint responds 422 without source/503 without implementation.
- BUG-017: QC fails closed on missing/unmatched inputs and on insufficient temporal frame evidence; scores are nullable instead of fabricated.
- BUG-008: storage accepts max_bytes, writes atomically, verifies PNG/JPEG/WebP bytes and pixel cap before publishing; corrupt files 422, oversize 413.
- BUG-005 partial: production-only Bearer access token with startup lockout if unset, CORS allowlist; **NOT tenant authentication**.
- BUG-006 partial: API container now copies shared packages and smoke-imports project.
- Regression tests: new `tests/unit/test_truthfulness_regressions.py`, updates existing e2e/master tests.
- CI: `.github/workflows/refactor-cpu-ci.yml` committed to implementation branch; **result pending until GitHub Actions runs**.
- Full P00 prerequisite still open: actual DB/storage backup and restore, clean full baseline tests, deployment-specific hardware verification.
- No GPU reconstruction, Blender execution, Wan inference or model license claims verified here. **G00 and G01 remain OPEN**.
