# Architecture — current implementation

## Phase

This repository is deliberately in **Phase 0/1 Core Engine**, not Phase 2 Hybrid GPU.

```text
Browser / Next.js
      |
      v
FastAPI  ----> PostgreSQL/SQLite
      |
      v
RenderJob ----> Redis queue (optional) / DB polling fallback
      |
      v
Worker
      |
      +--> safe source-motion renderer (working)
      +--> GeometryBackend (capability gate; COLMAP/3DGS next)
      |
      v
FFmpeg -> MP4
```

## Why the fallback is conservative

Until a scene has trustworthy geometry, the worker only uses original source pixels with small crop/pan/zoom and crossfade. It does not invent unseen architecture.

## Geometry integration contract

The next implementation should add a `GeometryBackend` that produces:

- registered camera intrinsics/extrinsics;
- sparse reconstruction statistics;
- scene representation URI/version;
- safe camera bounds;
- novel-view quality metrics.

Then the renderer can choose geometry only when the capability and quality gates pass.
