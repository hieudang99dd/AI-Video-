# AI-Video — evidence-based project status

**Canonical specification:** [MASTER_REFACTOR_PLAN.md](MASTER_REFACTOR_PLAN.md). This file is **not** a second roadmap.

**Baseline inspected:** `main` @ `87cc55241198d3654246ff3943a4c99c8b303063` (2026-10-13 ICT). Source review confirmed multiple modules exist, but **this documentation update did not run a fresh local test suite, GPU benchmark, clean Docker build, or live 3D inference.** Prior claims that 121 tests passed refer to earlier project reporting only and **are not independent proof for the current baseline**.

## Current phase

**P00 — NOT_STARTED** (baseline source inventory and planning produced; baseline tests, data backup/restore, tag, issues and clean builds still to be performed). Agent must begin with P00. No phase gate is marked passed.

## Phase tracker (complete the evidence before any GATE_PASSED)

| Phase | State | Evidence / PR | Critical blocker |
|---|---|---|---|
| P00 | NOT_STARTED | Plan and source static audit only | clean build/test/backup pending |
| P01 | NOT_STARTED | — | QC fake success, AI stub, auth/upload gaps |
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

- [ ] P00-01 baseline tag/backup and restore test
- [ ] P00-02 run `pytest`, Next build, CPU Docker clean build; save logs
- [ ] P00-03 inventory current endpoints and dataset artifacts
- [ ] P00-04 create prioritized issues BUG-001..BUG-030; assign phase owners
- [ ] P00-05 open controlled P01 feature branches; never fake completed

## Update protocol

For each merged PR add: date, HEAD SHA, issue IDs, phase, tests with exact commands and results, source dataset/version, output artifacts/ffprobe, GPU/VRAM if used, blockers, reviewer, fallback/rollback procedure. The phase gate may change to `GATE_PASSED` only when every criterion in `MASTER_REFACTOR_PLAN.md` is demonstrated.
