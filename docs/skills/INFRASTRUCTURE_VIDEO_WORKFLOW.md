# Quy trình sản xuất video hạ tầng kỹ thuật (Infrastructure Video Workflow)

Tài liệu này đặc tả quy trình chuyển đổi thư mục ảnh xuất từ **Autodesk Civil 3D** và **Autodesk InfraWorks** thành video giới thiệu dự án hạ tầng giao thông/kỹ thuật đô thị hoàn chỉnh.

## 1. Nguồn dữ liệu đầu vào đặc thù từ Civil 3D / InfraWorks

Trong các dự án hạ tầng giao thông và công trình xây dựng, ảnh xuất từ Civil 3D và InfraWorks thường có các dạng sau:

1. **Bình đồ tuyến (Plan View / Alignment):**
   - Ảnh chụp từ trên xuống (orthographic hoặc top-down perspective), hiển thị tim tuyến, cọc lý trình (Km0+000, Km1+500), ranh giải phóng mặt bằng, các nút giao và công trình lân cận.
2. **Trắc dọc tuyến (Profile View):**
   - Bản vẽ kỹ thuật thể hiện đường đen (cao độ tự nhiên), đường đỏ (cao độ thiết kế), độ dốc dọc $i\%$, bán kính đường cong đứng và vị trí cống/cầu.
3. **Mặt cắt ngang điển hình (Cross Sections):**
   - Thể hiện bề rộng làn đường, dải phân cách giữa, lề đường, mái taluy đắp/đào, mương thoát nước, kết cấu áo đường (bê tông nhựa, cấp phối đá dăm).
4. **Nút giao và công trình cầu/cống (Bridges, Culverts & Interchanges):**
   - Ảnh phối cảnh 3D từ InfraWorks mô phỏng cầu vượt, cống chui dân sinh, hầm chui, vòng xoay nút giao.
5. **Hệ thống hạ tầng kỹ thuật (Drainage, Lighting, Signage):**
   - Hệ thống thoát nước mưa/nước thải, hào kỹ thuật, cột đèn chiếu sáng, biển báo giao thông và hộ lan tôn sóng.

## 2. Quy trình sản xuất 7 bước (Folder-to-Video Pipeline)

```text
Thư mục ảnh (Civil 3D / InfraWorks)
   │
   ▼
[1. Import & Inspection] ──► Giữ nguyên ảnh gốc, phân tích kích thước, tỷ lệ, độ nét
   │
   ▼
[2. Phân loại theo Template] ──► Tự động hoặc thủ công gán nhãn: Tổng quan, Bình đồ, Trắc dọc, Mặt cắt, Cầu/Cống...
   │
   ▼
[3. Lập Storyboard & Shot List] ──► Xác định thứ tự diễn giải, thời lượng (ví dụ 5s/cảnh), tiêu đề kỹ thuật, phụ đề
   │
   ▼
[4. Chọn Chế độ Camera] ──► 2D_IMAGE_CAMERA (ưu tiên cho bản vẽ), 3D_SCENE_CAMERA (cho cảnh 3D overlap), AI (minh họa)
   │
   ▼
[5. Lồng tiếng & Phụ đề] ──► Nhập kịch bản thuyết minh (narration), phụ đề (subtitles), chọn nhạc nền (BGM)
   │
   ▼
[6. Render từng Shot qua Worker] ──► Background rendering, kiểm tra chuyển động an toàn, chống rung giật
   │
   ▼
[7. Ghép Timeline & Xuất MP4] ──► Hòa âm Audio, overlay tiêu đề/logo, Quality Control (QC) và tải video
```

## 3. Quy tắc bảo toàn hình học kỹ thuật (Engineering Geometry Fidelity)

- **Nguyên tắc số 1:** Không bao giờ dùng AI tạo video ngẫu nhiên (text-to-video / image-to-video tự do) để làm sai lệch kích thước hình học, độ dốc, số làn xe hoặc kết cấu công trình đã thiết kế trong Civil 3D.
- **Bản vẽ 2D (Bình đồ, Trắc dọc, Mặt cắt):** Luôn dùng chế độ `2D_IMAGE_CAMERA` với chuyển động camera tịnh tiến có kiểm soát (Pan dọc theo lý trình tim tuyến từ đầu tuyến đến cuối tuyến, Zoom nhẹ tập trung vào điểm nút quan trọng nhưng không vượt quá 1.35x để bảo toàn độ sắc nét của chữ số kỹ thuật).
- **Phối cảnh 3D xuất từ InfraWorks:** Nếu có chuỗi ảnh chụp góc liên tục xung quanh nút giao/cầu, kích hoạt `3D_SCENE_CAMERA`. Nếu chỉ có 1 ảnh phối cảnh tĩnh, dùng chuyển động `2D_IMAGE_CAMERA` (slow dolly-in hoặc pedestal up) để tạo cảm giác cinematic trang nhã mà không làm biến dạng mô hình.

