# Cẩm Nang Xử Lý Sự Cố (TROUBLESHOOTING.md)

Tài liệu này tổng hợp các tình huống lỗi thường gặp trong quá trình xử lý ảnh Civil 3D / InfraWorks, khôi phục 3D, dựng quỹ đạo camera và xuất bản video MP4, kèm theo cơ chế **Tự Động Chuyển Hướng (Graceful Fallback)** của hệ thống.

---

## 1. Lỗi Liên Quan Đến Ảnh Đầu Vào (Image Ingestion & Quality Analysis)

### 1.1. Tải lên chỉ 1 ảnh tĩnh duy nhất
- **Hiện tượng:** Người dùng chỉ tải lên 1 ảnh chụp phối cảnh từ Civil 3D / InfraWorks, không thể chạy COLMAP SfM.
- **Cách hệ thống xử lý:** Hệ thống không báo lỗi dừng pipeline. Thay vào đó, bộ điều phối tự động chọn chế độ **`C_SINGLE_IMAGE_2_5D`** (Chiếu 2.5D có chiều sâu giả lập và chuyển động Parallax nhẹ) kèm cảnh báo rõ ràng trong `manifest.json`.

### 1.2. Các ảnh không có vùng chồng lấp (Insufficient Overlap)
- **Hiện tượng:** Các ảnh chụp ở các lý trình cách xa nhau (ví dụ Km0+000 và Km25+000) hoặc gồm mặt cắt ngang 2D xen lẫn phối cảnh 3D (`overlap_score < 0.18`).
- **Cách hệ thống xử lý:**
  1. Hàm `estimate_pairwise_overlap()` (ORB + RANSAC Homography) phát hiện tỷ lệ trùng khớp thấp và gắn cờ `low_overlap_with_previous`.
  2. Nếu COLMAP không đăng ký đủ pose (`registered_images < 2`), hệ thống tự động chuyển sang **`B_ORDERED_IMAGE_PATH`** (hành trình bay qua các mốc cảnh theo thứ tự với chuyển tiếp Cross-fade / Dissolve mượt mà).

### 1.3. Ảnh trùng lặp hoặc gần trùng lặp (Duplicate / Near-Duplicate)
- **Hiện tượng:** Người dùng vô tình chọn xuất nhiều frame giống hệt nhau từ InfraWorks.
- **Cách hệ thống xử lý:** Hàm `compute_dhash()` tính khoảng cách Hamming 64-bit giữa các ảnh. Nếu `hamming_distance == 0` (trùng hoàn toàn) hoặc `<= 6` (gần trùng), hệ thống gắn nhãn `duplicate_of_asset_{id}` hoặc `near_duplicate_of_asset_{id}` trong kết quả phân tích để người dùng loại bỏ hoặc giữ lại tùy ý.

### 1.4. Ảnh bị mờ, thiếu sáng hoặc cháy sáng
- **Hiện tượng:** Ảnh chụp màn hình độ phân giải thấp hoặc thiếu tương phản.
- **Cách hệ thống xử lý:** Hệ thống đánh giá `sharpness_score` (Laplacian variance), `brightness_mean` và `contrast_std`, tự động phát cảnh báo `blurry_image`, `underexposed_dark` hoặc `overexposed_bright` trên bảng dữ liệu và `manifest.json`.

---

## 2. Lỗi Khôi Phục Cảnh 3D & Tỷ Lệ Hình Học (`scale_status: uncalibrated`)

### 2.1. Cảnh báo `scale_status = "uncalibrated"` trong Manifest
- **Nguyên nhân:** Ảnh xuất từ Civil 3D / InfraWorks thông thường (PNG/JPG) không chứa thông tin tọa độ trắc địa tuyệt đối (GCP - Ground Control Points) hoặc ma trận nội tại camera chuẩn xác.
- **Giải pháp:** Đây là **cơ chế minh bạch kỹ thuật bắt buộc** của hệ thống. Không gian 3D khôi phục được gán hệ tọa độ `uncalibrated_local` với đơn vị `relative_units`. Hệ thống tuyệt đối không bịa đặt kích thước mét thực tế nếu không có dữ liệu hiệu chuẩn.

### 2.2. Không tìm thấy `colmap` hoặc `blender` trong PATH
- **Hiện tượng:** API `/api/v1/capabilities` báo `"colmap": {"available": false}` hoặc `"blender": {"available": false}`.
- **Giải pháp:**
  - Hệ thống vẫn hoạt động bình thường 100% nhờ cơ chế xuất script Python Blender độc lập (`shot_{id}_blender.py`) và bộ kết xuất khung hình OpenCV + FFmpeg tích hợp sẵn.
  - Nếu muốn chạy COLMAP hoặc Blender CLI trực tiếp, hãy cài đặt và khai báo đường dẫn tuyệt đối trong `.env` (`IVB_COLMAP_PATH`, `IVB_BLENDER_PATH`).

---

## 3. Lỗi Kết Xuất Video (FFmpeg & MP4 Export)

### 3.1. Máy tính chưa cài đặt FFmpeg toàn cục (Global PATH)
- **Hiện tượng:** Lệnh `ffmpeg` trên terminal báo `CommandNotFoundException`.
- **Cách hệ thống xử lý:** Hệ thống đã tích hợp sẵn gói `imageio-ffmpeg`. Hàm `_resolve_ffmpeg()` trong `apps/api/app/services/capabilities.py` tự động dò tìm binary FFmpeg nội bộ của `imageio-ffmpeg` để mã hóa H.264 (`libx264`, `yuv420p`, `-movflags +faststart`) mà không cần người dùng cài đặt thủ công.

---

## 4. Lỗi Hậu Kỳ AI & Kiểm Định Chất Lượng (AI QC)

### 4.1. Bản hậu kỳ AI làm biến dạng kết cấu cầu / làn đường
- **Hiện tượng:** Khi thử nghiệm các mô hình sinh video AI bên ngoài, vạch kẻ đường hoặc trụ cầu có thể bị cong vênh (`Edge IoU < 0.72` hoặc `Structural Consistency < 0.80`).
- **Cách hệ thống xử lý:**
  1. Bộ kiểm định `evaluate_ai_enhancement_qc()` tự động đo độ trùng khớp cạnh Canny (`Edge IoU`), tương quan cấu trúc và độ ổn định liên khung hình (`Temporal Stability`).
  2. Nếu không đạt ngưỡng an toàn kỹ thuật, hệ thống tự động đánh dấu `passed = false`, đưa ra khuyến nghị `reject_ai_revert_to_3d`, và **giữ nguyên bản render 3D gốc** khi ghép video cuối cùng.
  3. Người dùng cũng có thể bấm nút **"↺ Từ chối & Quay về bản 3D Gốc"** ngay trên giao diện Studio.
