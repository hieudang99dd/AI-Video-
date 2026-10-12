# Project status

## Current phase

Phase 0 / early Phase 1 Core Engine.

## Verified now

- [x] source tree follows canonical skill boundaries
- [x] FastAPI API
- [x] project / asset / shot / RenderJob persistence
- [x] upload remains immutable in originals path
- [x] worker-based rendering; no long render inside HTTP request
- [x] FFmpeg H.264 output
- [x] conservative source-image fallback
- [x] capability gate for Geometry Mode
- [x] cancel flag and observable failure reason
- [x] camera quaternion SLERP unit tests
- [x] renderer integration test
- [x] end-to-end DB -> worker -> MP4 smoke test

## Not claimed complete

- [ ] COLMAP/PyCOLMAP reconstruction (Integration code done; Blocked by Environment)
- [ ] 3D Gaussian Splatting training/rendering (Integration code done via Nerfstudio; Blocked by Environment)
- [ ] geometry-derived keyframes/camera paths
- [ ] collision / visibility quality validation from reconstructed scene
- [ ] true depth-layer 2.5D
- [ ] temporal refinement AI
- [ ] Hybrid GPU Local Agent / Cloud Router (Phase 2 only)
- [ ] auth/billing/teams (later phase)

## Blockers
- **No CUDA GPU / Docker / COLMAP / Nerfstudio in Environment**: Integration code for `geometry_backend.py` is completed for both COLMAP SfM and 3DGS (`ns-train` / `ns-render`). However, the environment lacks Docker, COLMAP, FFMPEG, and a compatible NVIDIA CUDA GPU to run the acceptance tests. The integration gracefully reports `unavailable` (via capabilities) and raises appropriate errors without faking the results.

The repository must not advertise Geometry Mode as working until the Phase 0 feasibility gate passes.
