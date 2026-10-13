# Giấy Phép Bản Quyền Các Mô Hình & Công Cụ Tích Hợp (MODEL_LICENSES.md)

Tài liệu này liệt kê minh bạch toàn bộ giấy phép bản quyền (License), phạm vi sử dụng thương mại / phi thương mại, và cơ chế kiểm soát (License Gate) của từng công cụ và mô hình AI trong hệ thống **AI-Video**.

---

## 1. Bảng Tổng Hợp Giấy Phép (License Matrix)

| Thành phần / Mô hình | Vai trò trong Pipeline | Giấy phép (License) | Sử dụng Thương Mại | Trạng thái Mặc Định | Cơ chế Kiểm Soát (Gate) |
|---|---|---|---|---|---|
| **FastAPI / SQLAlchemy / Pydantic** | Core Backend & API | MIT License | ✅ Cho phép | Bật sẵn | Core Dependency |
| **OpenCV (`opencv-python-headless`)** | Phân tích ảnh, ORB, RANSAC, QC | Apache License 2.0 | ✅ Cho phép | Bật sẵn | Core Dependency |
| **FFmpeg (`imageio-ffmpeg`)** | Ghép và mã hóa video MP4 H.264 | LGPL / GPL (Binary) | ✅ Cho phép | Bật sẵn | Tự động phát hiện |
| **COLMAP** | Khôi phục cảnh 3D (SfM / MVS) | BSD 3-Clause (mới) | ✅ Cho phép | Tùy chọn | `IVB_COLMAP_PATH` |
| **Blender** | Dựng cảnh 3D & Camera Trajectory | GNU GPL v2 / v3 | ✅ Cho phép (Output thuộc về người dùng) | Tùy chọn | `IVB_BLENDER_PATH` |
| **Wan2.2 (`Wan2.2-TI2V-5B`, `A14B`)** | Hậu kỳ chất lượng video AI | **Apache License 2.0** | ✅ Cho phép | Tắt (Optional) | `IVB_WAN_ENABLED=true` |
| **MoVerse** | Novel View Synthesis dọc quỹ đạo | **Apache License 2.0** | ✅ Cho phép | Tắt (Optional) | `IVB_MOVERSE_ENABLED=true` |
| **DUSt3R (`naver/dust3r`)** | Khôi phục 3D đa góc nhìn (Ít ảnh) | **CC BY-NC-SA 4.0** (Code + Checkpoint) | ❌ **KHÔNG (Chỉ Phi Thương Mại / Nghiên Cứu)** | **Khóa mặc định** | Bắt buộc bật `IVB_ALLOW_NON_COMMERCIAL_MODELS=true` |

---

## 2. Chi Tiết Quy Định Sử Dụng Từng Nhóm Mô Hình

### 2.1. Nhóm Cho Phép Thương Mại (`Apache-2.0` / `MIT` / `BSD`)
- **Wan2.2 (`Wan-AI/Wan2.2-TI2V-5B`)**: Phát hành theo giấy phép **Apache-2.0**. Cho phép sử dụng trong cả môi trường nghiên cứu và sản phẩm thương mại. Tuy nhiên, mọi phân cảnh sử dụng hậu kỳ Wan2.2 trong hệ thống đều bắt buộc:
  1. Qua bước kiểm định hình học `evaluate_ai_enhancement_qc()` (Edge IoU ≥ 0.72, Structural Consistency ≥ 0.80).
  2. Gắn nhãn `AI_ENHANCED` và tuyên bố miễn trừ trách nhiệm kỹ thuật (`ai_disclaimer`) trong `manifest.json` và trên khung hình xuất bản.
- **MoVerse**: Phát hành theo giấy phép **Apache-2.0**. Được đóng gói dưới dạng Optional Adapter (`MoVerseAdapter`) để hỗ trợ sinh góc nhìn mới khi có GPU ≥ 12 GB VRAM.

### 2.2. Nhóm Giới Hạn Phi Thương Mại (`CC BY-NC-SA 4.0`)
- **DUSt3R (Naver Labs Europe)**:
  - Phần mã nguồn chính và các trọng số huấn luyện sẵn (pretrained checkpoints) của DUSt3R chịu sự điều chỉnh của giấy phép **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.
  - **Cơ chế bảo vệ trong mã nguồn (`DUSt3RAdapter`):**
    - Mặc định `IVB_DUST3R_ENABLED=false` và `IVB_ALLOW_NON_COMMERCIAL_MODELS=false`.
    - Nếu người vận hành bật `IVB_DUST3R_ENABLED=true` nhưng **không** bật `IVB_ALLOW_NON_COMMERCIAL_MODELS=true`, hệ thống sẽ từ chối nạp trọng số DUSt3R và trả về thông báo cảnh báo bản quyền rõ ràng qua API `/api/v1/ai-modules/status`.

---

## 3. Cam Kết Minh Bạch Kỹ Thuật (Engineering Integrity Disclaimer)

Bất kể sử dụng công cụ nào trong danh mục trên, hệ thống tuân thủ nghiêm ngặt 3 nguyên tắc:
1. **Không tuyên bố khôi phục chính xác mô hình BIM từ ảnh tĩnh:** Cảnh 3D tái tạo từ ảnh tĩnh không có mốc tọa độ thực địa luôn được ghi nhận rõ `scale_status = "uncalibrated"` và `unit = "relative_units"`.
2. **Bảo toàn hình học công trình là ưu tiên số 1:** Mọi bước hậu kỳ AI đều chỉ đóng vai trò tùy chọn (`Optional`) sau khi đã có đường bay camera 3D ổn định.
3. **Quyền kiểm soát cuối cùng thuộc về kỹ sư:** Kỹ sư sử dụng phần mềm luôn có quyền xem bảng chỉ số QC, so sánh và bấm **Từ chối AI (Revert về bản 3D gốc)** bất cứ lúc nào.
