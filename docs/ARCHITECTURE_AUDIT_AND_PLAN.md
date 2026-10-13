# BÁO CÁO KIỂM ĐỊNH KIẾN TRÚC HIỆN TẠI, RỦI RO & KẾ HOẠCH NÂNG CẤP (PHASE 0 AUDIT)

## 1. Kiến trúc hiện tại của Repository (`AI-Video-`)

Qua quá trình kiểm tra toàn bộ mã nguồn hiện có, hệ thống bao gồm các thành phần sau:

- **Backend API (`apps/api`)**:
  - Framework: **FastAPI** + **SQLAlchemy 2.0** (SQLite mặc định, hỗ trợ PostgreSQL) + **Pydantic v2**.
  - Lưu trữ (`app/services/storage.py`): `LocalStorage` lưu file an toàn dưới `storage_root` với URI dạng `local://...` và băm `sha256`.
  - Hàng đợi & Worker (`app/services/queue.py`, `app/workers/render_worker.py`): Hỗ trợ Redis (`lpush`/`brpop`) kèm cơ chế fallback polling trực tiếp từ bảng `RenderJob` trong cơ sở dữ liệu.
  - Phân tích ảnh (`app/services/image_analysis.py`): Đánh giá kích thước, độ sáng (`exposure_score`), độ sắc nét (`sharpness_score` bằng Laplacian phương sai) qua Pillow / OpenCV.
  - Tái dựng hình học (`app/services/geometry_backend.py`): Có `CapabilityGatedGeometryBackend` tích hợp CLI **COLMAP** (`feature_extractor`, `matcher`, `mapper`, `model_converter`) và **Nerfstudio** (`ns-train splatfacto`, `ns-render camera-path`).
  - Render & Xuất video (`app/services/renderer.py`): Có `render_safe_motion` (chuyển động 2.5D bảo toàn hình học trên ảnh gốc), `render_geometry_motion` (render từ 3DGS khi có GPU + Nerfstudio) và `concatenate_timeline` ghép MP4 bằng **FFmpeg**.
- **Gói thư viện toán học & hình học (`packages/`)**:
  - `packages/camera_math`: Nội suy vị trí (`lerp`, `catmull_rom`), nội suy hướng xoay Quaternion (`slerp`), hàm easing (`cinematic_ease`).
  - `packages/colmap`: `ColmapRepository` đọc trực tiếp mô hình thưa (`cameras.txt`, `images.txt`, `points3D.txt`, `database.db`) bằng Python chuẩn + `sqlite3`.
  - `packages/geometry`: Chuyển đổi hệ tọa độ (`coords.py`), chọn keyframe (`keyframes.py`), tài liệu đường bay camera (`CameraPathDocument` trong `camera_path.py`).
  - `packages/path_validation`: `PathValidator` và `PointCloudProxy` kiểm tra va chạm, vận tốc góc, độ mượt và vùng tin cậy.
  - `packages/scene_grouping`: `SceneGrouper` gom cụm ảnh theo đồ thị hình học (`PairRelation`).
- **Frontend (`index.html`, `docs/index.html`, `apps/api/app/ui.py`, `apps/web`)**:
  - Giao diện SPA phục vụ cả chế độ tĩnh (GitHub Pages) và kết nối với FastAPI backend (`/ui`).
- **Môi trường phần cứng hiện tại**:
  - OS: Windows, Python 3.12.10 (`uv`).
  - GPU: **NVIDIA GeForce RTX 5070 Ti (16GB VRAM)**, Driver 576.88, CUDA 12.9.
  - FFmpeg: Đã tích hợp qua `imageio-ffmpeg` (cung cấp binary `ffmpeg` thực tế ngay trong `.venv`).
  - COLMAP / Blender / Nerfstudio CLI: Chưa cài trong `PATH` hệ thống; cần cơ chế capability gate rõ ràng + sinh script Blender chuẩn + fallback renderer thực tế.

---

## 2. Các rủi ro kỹ thuật & Pháp lý cần kiểm soát

1. **Rủi ro phóng đại độ chính xác hình học (BIM Hallucination)**:
   - Ảnh tĩnh xuất từ Civil 3D / InfraWorks không mang hệ tọa độ quốc gia (VN-2000) hay tỷ lệ kích thước thực nếu không có dữ liệu trắc địa đi kèm.
   - *Giải pháp*: Luôn gắn nhãn `scale_status = "uncalibrated"` và `unit = "relative_units"` trừ khi có mốc tọa độ thực; phân biệt rõ 3 nguồn camera: **(A) 3D Reconstructed**, **(B) Ordered Image Path**, **(C) Single-Image 2.5D**.
2. **Rủi ro biến dạng công trình khi dùng AI Video (Wan2.2 / MoVerse)**:
   - Các mô hình khuếch tán sinh video có thể làm cong dầm cầu, lệch vạch kẻ đường hoặc thay đổi số làn xe.
   - *Giải pháp*: Tắt AI mặc định; tách riêng thành worker/job tùy chọn; bắt buộc đi qua module **AI Quality Control (AI QC)** đo độ lệch cạnh kết cấu (Edge IoU), độ ổn định khung hình (Temporal Flicker) và cho phép người dùng duyệt/từ chối từng cảnh.
3. **Rủi ro giấy phép mã nguồn & mô hình (License Compliance)**:
   - **DUSt3R** sử dụng giấy phép **CC BY-NC-SA 4.0** (Phi thương mại). Không được bật mặc định trong cấu hình thương mại.
   - **Blender** sử dụng **GPL-2.0+**: Chỉ giao tiếp qua tiến trình CLI độc lập (`blender -b -P script.py`), tuyệt đối không nhúng mã GPL vào tiến trình Python của API.
   - **Wan2.2 (TI2V-5B / A14B)** sử dụng **Apache-2.0**: Cho phép sử dụng thương mại nhưng yêu cầu kiểm tra VRAM và tải trọng số riêng.
4. **Rủi ro thiếu phụ thuộc trên máy người dùng (COLMAP / Blender / Redis)**:
   - *Giải pháp*: Thiết kế theo kiến trúc Optional Dependency. Khi không có Redis, chạy `BackgroundTaskRunner` nội bộ. Khi không có `ffmpeg` trên PATH, tự động dùng binary từ `imageio_ffmpeg`. Khi không có Blender CLI, vẫn xuất file `.py` Blender + `.json` trajectory và kết xuất bằng engine 2.5D/3D Projection nội bộ để không làm đứt gãy luồng xuất MP4.

---

## 3. Kế hoạch thực hiện (7 Phases)

- **Phase 1 — Foundation**: Mở rộng schema `Project`, `ImageAsset`, `Scene`, `Shot`, `RenderJob`, thêm `AIJob`; xây dựng `JobStateMachine` (`CREATED` → `VALIDATING` → `RECONSTRUCTING` → `CAMERA_PLANNING` → `RENDERING` → `AI_ENHANCEMENT` → `COMPOSING` → `COMPLETED`) và `BackgroundTaskRunner`.
- **Phase 2 — Image Ingestion & Manifest**: Upload nhiều ảnh, phát hiện ảnh trùng/gần trùng (SHA-256 + Perceptual dHash), đánh giá độ mờ/độ sáng/độ chồng phủ ORB, phân loại hạng mục công trình (toàn cảnh, nút giao, cầu, cống, mặt đường...) và lưu `manifest.json`.
- **Phase 3 — Camera Planner**: Triển khai 10 Camera Presets chuẩn hạ tầng (Establishing, Aerial Flyover, Follow Road, Approach, Orbit, Intersection Reveal, Bridge Pass, Culvert/Drainage Detail, Low-angle Road, Closing Shot) và 3 chế độ camera A/B/C.
- **Phase 4 — Blender Render Engine**: Xây dựng `BlenderRenderEngine` sinh script Python Blender chuẩn (`.py`) dựng scene, point cloud/image plane, camera keyframe spline, ánh sáng và gọi CLI `blender -b` hoặc fallback sang projection renderer.
- **Phase 5 — COLMAP & DUSt3R Integration**: Chuẩn hóa adapter COLMAP và adapter tùy chọn DUSt3R (kèm cổng kiểm tra giấy phép CC BY-NC-SA 4.0), báo cáo độ tin cậy và tự động chuyển chế độ an toàn khi thiếu overlap.
- **Phase 6 — Optional AI (MoVerse & Wan2.2) + AI Quality Control**: Xây dựng `MoVerseAdapter`, `Wan22Adapter` (kiểm tra GPU/VRAM/weights/seed/timeout) và `AIQualityController` so sánh khung hình gốc vs. AI.
- **Phase 7 — Video Composer, 6-Screen Frontend, Docs & Testing**: Nâng cấp `VideoComposer` (FFmpeg chuẩn hóa FPS/độ phân giải/âm thanh/tiêu đề), nâng cấp giao diện 6 màn hình chuyên nghiệp, viết 4 tài liệu (`INSTALL.md`, `GPU_SETUP.md`, `TROUBLESHOOTING.md`, `MODEL_LICENSES.md`) và bộ kiểm thử Unit/Integration/Failure.
