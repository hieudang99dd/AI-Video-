# Render, Lắp ráp và Xuất bản Video (Render & Export Pipeline)

Tài liệu này đặc tả quy trình render qua Background Worker, lắp ráp âm thanh/phụ đề, kiểm định chất lượng (Quality Control - QC) và cơ chế tải video MP4 thành phẩm.

## 1. Kiến trúc luồng Render an toàn

```text
Yêu cầu Render (Shot hoặc Full Timeline Project)
   │
   ▼
[API: /shots/{id}/preview hoặc /projects/{id}/render]
   │
   ▼
Tạo `RenderJob` (status = "queued") trong Database
   │
   ▼
Đẩy job ID vào Queue (Redis List hoặc DB Polling fallback)
   │
   ▼
[Render Worker] ──► Nhận job, đổi status = "processing", cập nhật progress định kỳ
   ├── 1. Kiểm duyệt Camera Path / Asset resolution
   ├── 2. Sinh chuỗi frame hình ảnh theo FPS (24/25/30)
   ├── 3. Thêm overlay tiêu đề kỹ thuật và phụ đề lên từng frame (hoặc qua FFmpeg)
   ├── 4. Mã hóa chuỗi frame bằng FFmpeg (libx264, yuv420p, +faststart)
   ├── 5. Hòa âm Audio (Narration voiceover + BGM với volume ducking)
   └── 6. Kiểm định chất lượng video xuất (QC Step)
   │
   ▼
Lưu trữ video vào Storage (`storage_root`), cập nhật status = "completed"
   │
   ▼
Người dùng tải video MP4 hoặc xem trực tiếp trên Web UI
```

## 2. Tiêu chuẩn mã hóa Video và Audio

- **Video Codec:** `H.264` (`libx264`), profile High, pixel format `yuv420p` (tương thích 100% với trình duyệt web Safari, Chrome, Edge và thiết bị di động).
- **Flag Web Streaming:** `-movflags +faststart` (cho phép phát video ngay lập tức trong khi tải dữ liệu).
- **Khung hình (FPS):** Mặc định $30\text{ fps}$ (hỗ trợ $24, 25\text{ fps}$ theo chuẩn truyền hình).
- **Độ phân giải:**
  - Preview: $1280 \times 720$ (720p).
  - Final Render: $1920 \times 1080$ (1080p).
- **Audio Codec:** `AAC` stereo, bitrate $192\text{ kbps}$, sample rate $44100\text{ Hz}$ hoặc $48000\text{ Hz}$.
- **Audio Ducking:** Khi có giọng đọc thuyết minh (Narration), âm lượng nhạc nền (BGM) tự động giảm xuống $15 - 20\%$ để làm rõ lời thoại.

## 3. Khâu kiểm định chất lượng đầu ra (Quality Control - QC)

Hệ thống **tuyệt đối không đánh dấu `status = "completed"`** nếu chưa thỏa mãn toàn bộ các điều kiện sau:

1. **Sự tồn tại của tệp:** Tệp MP4 tồn tại tại đường dẫn đích.
2. **Kích thước tệp:** Dung lượng tệp $> 1024\text{ bytes}$ (tránh tệp 0 byte do FFmpeg thoát sớm).
3. **Thời lượng video:** Thời lượng thực tế sai lệch không quá $\pm 0.5\text{ giây}$ so với thời lượng mong muốn của shot/timeline.
4. **Khả năng giải mã:** Gọi FFprobe hoặc kiểm tra header container của video để bảo đảm không bị lỗi hỏng (corrupted bitstream).

Nếu không đạt QC, job được chuyển sang `status = "failed"` kèm thông báo lỗi chi tiết để hỗ trợ retry/resume.

