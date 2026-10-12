# Phase 0 benchmark dataset manifest

Create versioned datasets before declaring Geometry Mode viable.

| Dataset ID | Expected mode | Purpose |
|---|---|---|
| exterior-easy-v1 | geometry | good overlap, stable lighting |
| interior-easy-v1 | geometry | textured room, moderate baseline |
| sparse-v1 | fallback | weak overlap; must not fake geometry |
| single-image-v1 | 2.5d_lite | conservative source-image motion |
| disconnected-v1 | transition | exterior + unrelated interior |

For every run record: image count, registered ratio, processing time, peak VRAM/RAM, output video, failure reason, and engine/config versions.
