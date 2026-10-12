# Phase 0 Exit Checklist

- [x] Project + immutable image upload
- [x] Image QA metrics & sharpness/exposure scoring
- [x] Persistent RenderJob state machine & provenance
- [x] Worker abstraction & safe source-image fallback
- [x] Cancel flag / timeout handling / process runner with tree kill
- [x] Capability detection contract with granular train/render/CUDA metrics
- [x] Camera math & quaternion SLERP tests
- [x] COLMAP SfM pipeline adapter & text model parser
- [x] Registered-camera export & Nerfstudio dataset generator
- [x] 3DGS backend (splatfacto train/render adapter)
- [x] Canonical camera path schema & API (GET/PUT/validate)
- [x] Geometry view-quality validation (PathValidator & PointCloudProxy)
- [x] Video quality control (FFprobe codec/resolution/duration/stream inspection)
- [x] Geometric scene grouping (SceneGrouper with union-find)
- [ ] Exterior benchmark pass on live GPU (Blocked by Environment: host has Radeon 520 / Intel UHD, no CUDA GPU)
- [ ] Interior benchmark pass on live GPU (Blocked by Environment: host has Radeon 520 / Intel UHD, no CUDA GPU)

> **Lưu ý:** Hybrid GPU và Cloud GPU worker chỉ được triển khai sau khi benchmark trên GPU thật đạt yêu cầu.
