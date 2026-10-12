# Yêu cầu phần cứng và Benchmark hiệu năng (Hardware & Benchmarks)

Tài liệu này ghi nhận yêu cầu phần cứng tối thiểu, khuyến nghị và cơ chế tự động chuyển đổi cấu hình (Fallback Matrix) khi môi trường không đủ điều kiện.

## 1. Bảng yêu cầu phần cứng theo chế độ hoạt động

| Chế độ thực thi | Phần cứng tối thiểu | Phần cứng khuyến nghị | Khả năng hoạt động khi thiếu phần cứng |
|---|---|---|---|
| **`2D_IMAGE_CAMERA` (CPU Safe Fallback)** | CPU 2 Cores, 4GB RAM, không cần GPU | CPU 4+ Cores, 8GB+ RAM, SSD | **Mặc định hoạt động trên mọi máy tính** (kể cả laptop văn phòng, VPS không GPU). |
| **Hòa âm & Render MP4 (FFmpeg)** | CPU 2 Cores, 4GB RAM | CPU 4+ Cores, hỗ trợ OpenCL hoặc Intel QuickSync / NVENC | Có thể chạy hoàn toàn bằng phần mềm (`libx264` CPU mode). |
| **`3D_SCENE_CAMERA` (COLMAP SfM)** | CPU 4 Cores, 16GB RAM | CPU 8 Cores, 32GB RAM, GPU NVIDIA CUDA (6GB+ VRAM) | Nếu không có GPU CUDA, COLMAP có thể chạy CPU SIFT nhưng tốc độ chậm; nếu thiếu COLMAP thì tự động fallback về 2D. |
| **`3D_SCENE_CAMERA` (3DGS / Nerfstudio)** | GPU NVIDIA 8GB VRAM (RTX 3060 / 4060) | GPU NVIDIA 16GB - 24GB VRAM (RTX 3090 / 4090 / A10) | **Bắt buộc có CUDA GPU**. Không chạy được trên CPU thuần; tự động báo `unavailable` và từ chối render 3DGS giả tạo. |
| **`AI_VIDEO_CAMERA` (Wan2.2 / ComfyUI)** | GPU NVIDIA 12GB VRAM (chạy bản quantized Q4/Q8) | GPU NVIDIA 24GB+ VRAM | Nếu thiếu GPU AI, adapter tự động tắt và giữ nguyên workflow không dùng AI. |

## 2. Ma trận Fallback tự động (Fallback Matrix)

```text
[Phát hiện tài nguyên máy tính]
   ├── Có GPU NVIDIA CUDA (>= 8GB VRAM) + COLMAP + 3DGS
   │      └── Mở quyền: `3D_SCENE_CAMERA` & `Geometry Mode`
   ├── Có GPU NVIDIA CUDA (>= 12GB VRAM) + ComfyUI online
   │      └── Mở quyền tùy chọn: `AI_VIDEO_CAMERA`
   └── Máy chỉ có CPU / Không có GPU CUDA
          └── Kích hoạt tự động: `2D_IMAGE_CAMERA` (CPU Safe Fallback)
```

## 3. Đo lường hiệu năng thực tế (Telemetry & Metrics)

Mỗi job render khi hoàn tất đều lưu lại các chỉ số sau vào `RenderJob.provenance`:
- `duration_sec`: Thời gian thực tế của video tạo ra.
- `render_wall_time_sec`: Thời gian xử lý của worker.
- `frame_count`: Tổng số khung hình đã render.
- `effective_fps`: Tốc độ sinh khung hình (frames / giây).
- `hardware_mode`: `"cpu_safe"` hoặc `"cuda_accelerated"`.
- `peak_ram_mb`: Mức tiêu thụ bộ nhớ RAM cao nhất (nếu có telemetry).
