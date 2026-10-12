# Project status

## Current phase

Phase 0 / early Phase 1 Core Engine.

## Verified now

- [x] source tree follows canonical skill boundaries
- [x] FastAPI API with infrastructure endpoints
- [x] project / asset / shot / RenderJob persistence
- [x] upload remains immutable in originals path
- [x] worker-based rendering; no long render inside HTTP request
- [x] FFmpeg H.264 output & timeline concatenation
- [x] conservative source-image fallback with engineering fidelity (2D_IMAGE_CAMERA)
- [x] 8 standard infrastructure video templates (`app/services/infrastructure_templates.py`)
- [x] 3 camera modes taxonomy & quality gate validation (`app/services/camera_modes.py`)
- [x] out-of-process AI Provider Adapter with safe fallback (`app/services/ai_adapter.py`)
- [x] technical title & subtitle overlay rendering
- [x] video export Quality Control (QC) validation
- [x] full project timeline assembly job queue
- [x] camera quaternion SLERP unit tests
- [x] 121 unit & API tests passing cleanly
- [x] supplementary domain guides (`docs/skills/*`) & external source map

## Not claimed complete

- [ ] COLMAP/PyCOLMAP live GPU reconstruction (Integration code done; Blocked by Environment)
- [ ] 3D Gaussian Splatting training/rendering (Integration code done via Nerfstudio; Blocked by Environment)
- [ ] collision / visibility quality validation from reconstructed scene on live mesh
- [ ] true depth-layer 2.5D
- [ ] Hybrid GPU Local Agent / Cloud Router (Phase 2 only)
- [ ] auth/billing/teams (later phase)

## Blockers
- **No CUDA GPU / Docker / COLMAP / Nerfstudio in Environment**: Integration code for `geometry_backend.py` is completed for both COLMAP SfM and 3DGS (`ns-train` / `ns-render`). However, the environment lacks Docker, COLMAP, FFMPEG, and a compatible NVIDIA CUDA GPU to run the acceptance tests. The integration gracefully reports `unavailable` (via capabilities) and raises appropriate errors without faking the results. Fallback to `2D_IMAGE_CAMERA` guarantees 100% video generation without hallucination.

The repository must not advertise Geometry Mode as working until the Phase 0 feasibility gate passes.
