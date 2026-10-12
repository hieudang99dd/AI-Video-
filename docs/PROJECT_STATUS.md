# Project Status

## Trạng thái thực tế (Verified Baseline)

- **Ngày xác minh:** 2026-10-12
- **Branch:** `main`
- **Bộ test:** 144 unit & integration tests pass sạch (`pytest -v`), 1 skipped (renderer smoke khi thiếu binary).

## Môi trường kiểm thử hiện tại

| Thành phần | Phiên bản / Trạng thái | Ghi chú |
|---|---|---|
| OS | Windows 10/11 x64 | PowerShell |
| Python | 3.13.15 (uv environment `.venv`) | CPython 64-bit |
| Node.js / npm | v24.21.0 / 11.19.0 | Next.js 16 / React 19 |
| GPU | AMD Radeon 520 (2GB) + Intel UHD 620 | **Không có NVIDIA CUDA GPU** |
| CUDA | `torch.cuda.is_available() == False` | Không có phần cứng NVIDIA |
| Docker | Chưa cài đặt trên host Windows | Đã sửa cấu hình Dockerfile & Dockerfile.gpu |
| COLMAP | Chưa cài đặt trên host Windows | Adapter kiểm tra capability, raise lỗi rõ ràng |
| Nerfstudio / ns-train / ns-render | Chưa cài đặt trên host Windows | Adapter kiểm tra capability, raise lỗi rõ ràng |

## Các hạng mục đã hoàn thành theo kế hoạch (Done)

- [x] **PR-01: Baseline & Documentation**: Ghi nhận toàn bộ thông số môi trường, cấu hình và blocker theo tiêu chuẩn Phase 0.
- [x] **PR-02: Python packaging & CPU Docker**:
  - Tạo `packages/__init__.py` chuẩn hóa namespace.
  - Sửa `apps/api/Dockerfile`: copy `packages` vào image và thiết lập `ENV PYTHONPATH="/app"`.
  - Kiểm tra import thành công cho cả `app.main`, `app.services.geometry_backend`, `packages.geometry.camera_path`.
- [x] **PR-03: GPU Docker Image Cleanup**:
  - Làm sạch `apps/api/Dockerfile.gpu`: dùng 1 base image chuẩn `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel`.
  - Loại bỏ các lệnh cài trùng lặp, copy đúng đường dẫn `apps/api/scripts/check_gpu_env.py` và `packages`.
- [x] **PR-04: Capability Contract & Process Runner**:
  - Chuẩn hóa `apps/api/app/services/capabilities.py` với các trường chi tiết: `colmap.available`, `cuda.available`, `cuda.error`, `nerfstudio.train_available`, `nerfstudio.render_available`, `geometry.reconstruct_available`, `geometry.train_available`, `geometry.render_available`.
  - Xây dựng module `apps/api/app/services/process_runner.py`: thực thi subprocess an toàn, argument list, timeout, cancellation với process tree kill, làm sạch thông tin nhạy cảm và unit tests toàn diện.
- [x] **PR-05 & PR-06: Geometry Quality Gate & Diagnostics**:
  - `apps/api/app/services/geometry_backend.py` tích hợp `process_runner`.
  - Tạo và lưu `input_manifest.json` ghi nhận asset checksum, file size, index trước khi chạy COLMAP.
  - Phân tách workspace an toàn, ghi nhận diagnostics chi tiết.
- [x] **PR-08: Video QC Inspection (FFprobe)**:
  - Nâng cấp `qc_video_output` trong `apps/api/app/services/renderer.py` để phân tích chuyên sâu container/streams qua `ffprobe` (codec, resolution, duration, audio streams) và fallback an toàn khi thiếu binary.
- [x] **PR-10: Camera Path API & Validation**:
  - Bổ sung trường `camera_path_doc` trong model `Shot`.
  - Xây dựng schema chuẩn Pydantic: `CameraKeyframeSchema`, `CameraPathDocSchema`, `CameraPathValidationResultSchema`.
  - Thêm các endpoint: `GET /api/v1/shots/{shot_id}/camera-path`, `PUT /api/v1/shots/{shot_id}/camera-path`, `POST /api/v1/shots/{shot_id}/camera-path/validate`.
- [x] **PR-12: Scene Grouping API**:
  - Thêm endpoint `POST /api/v1/projects/{project_id}/group-scenes` tích hợp `packages/scene_grouping/grouper.py`.
- [x] **PR-13: Giao diện Đồng bộ Quy trình Chuẩn Mới (UI Synchronization)**:
  - Đồng bộ `apps/api/app/ui.py` và `apps/web/app/page.tsx` theo đầy đủ 4 bước quy trình chuẩn.
  - Hiển thị trực quan Capability Matrix (phản ánh trung thực GPU CUDA, CPU Safe Motion fallback, COLMAP, Nerfstudio, FFmpeg/FFprobe).
  - Tích hợp tính năng gom nhóm Scene hình học tự động (`group-scenes`).
  - Trình biên tập Camera Path & Keyframes tương tác: hỗ trợ Motion Presets (Push-In, Orbit 360, Pan Ngang, Crane Fly-Through), thêm/xóa keyframe, kiểm tra tính hợp lệ (`validate`) với điểm số và lý do từ chối, và lưu trực tiếp lên server.
  - Nâng cấp quản lý Job & Deep QC Inspector: hỗ trợ hủy render (`cancel`), hiển thị chi tiết thông số FFprobe (container, codec, resolution, duration, audio stream, pixel format).
  - Bổ sung unit test `tests/unit/test_ui.py` kiểm thử các endpoint và thành phần UI (146 passed).

## Blockers & Trạng thái chưa kiểm chứng (Unverified / Blocked)

- **Chưa thể benchmark trực tiếp trên GPU máy này**: Host dev hiện tại chỉ có GPU AMD Radeon 520 (2GB) và Intel UHD 620, không hỗ trợ NVIDIA CUDA để chạy huấn luyện 3DGS Nerfstudio thật. Mã nguồn tích hợp đã sẵn sàng và capability gate phản ánh trung thực trạng thái này (không fake kết quả).
- Khi có máy tính công ty trang bị card NVIDIA RTX, chỉ cần chạy benchmark `docs/BENCHMARK_DATASETS.md` để đạt mốc `VERIFIED ON GPU`.
