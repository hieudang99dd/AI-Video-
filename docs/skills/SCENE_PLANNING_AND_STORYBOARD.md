# Kế hoạch phân cảnh và Storyboard (Scene Planning & Storyboard)

Tài liệu này định nghĩa cấu trúc phân cảnh, shot list, thời lượng, kịch bản thuyết minh và giao diện kiểm duyệt storyboard cho video dự án hạ tầng kỹ thuật.

## 1. Hệ thống 8 Template phân cảnh chuẩn cho hạ tầng

Một video giới thiệu dự án hạ tầng chuyên nghiệp thường kéo dài từ 45 giây đến 3 phút, bao gồm 8 phân cảnh logic:

| STT | Mã phân cảnh (`template_id`) | Tên phân cảnh | Mục đích & Nội dung hiển thị | Thời lượng đề xuất | Chế độ Camera khuyến nghị |
|---|---|---|---|---|---|
| 1 | `project_overview` | **Tổng quan dự án** | Phối cảnh tổng thể dự án từ InfraWorks, giới thiệu tên công trình, địa điểm, chủ đầu tư và tổng mức đầu tư. | 5 – 8 giây | `2D_IMAGE_CAMERA` (Slow zoom out / Flyover) |
| 2 | `alignment_plan` | **Bình đồ tuyến** | Bản vẽ bình đồ tuyến từ Civil 3D, làm nổi bật tim tuyến chính, các nhánh rẽ và ranh GPMB. | 6 – 10 giây | `2D_IMAGE_CAMERA` (Pan dọc tim tuyến theo hướng Km0 -> KmEnd) |
| 3 | `profile_view` | **Trắc dọc thiết kế** | Bản vẽ trắc dọc thiết kế, hiển thị đường đỏ, độ dốc dọc, các công trình thoát nước trên tuyến. | 5 – 8 giây | `2D_IMAGE_CAMERA` (Pan ngang theo đường đỏ thiết kế) |
| 4 | `cross_sections` | **Mặt cắt ngang điển hình** | Mặt cắt ngang tiêu chuẩn thể hiện làn xe cơ giới, lề đường, dải phân cách và kết cấu nền móng. | 5 – 8 giây | `2D_IMAGE_CAMERA` (Zoom in vào chi tiết làn và kết cấu) |
| 5 | `bridges_interchanges` | **Cầu, cống & Nút giao** | Phối cảnh 3D nút giao khác mức, cầu vượt sông hoặc hầm chui dân sinh từ InfraWorks. | 6 – 12 giây | `3D_SCENE_CAMERA` (nếu có chuỗi ảnh) hoặc `2D_IMAGE_CAMERA` |
| 6 | `drainage_system` | **Hệ thống thoát nước** | Bản vẽ hoặc mô hình 3D cống hộp, cống tròn, mương rãnh dẫn dòng và hồ điều hòa. | 5 – 8 giây | `2D_IMAGE_CAMERA` (Pan nhẹ dọc hệ thống thoát nước) |
| 7 | `traffic_safety` | **An toàn giao thông** | Hệ thống biển báo, sơn kẻ vạch, dải phân cách mềm, hộ lan tôn sóng và đèn tín hiệu. | 5 – 8 giây | `2D_IMAGE_CAMERA` (Pan tầm thấp ngang vạch sơn/hộ lan) |
| 8 | `project_outro` | **Kết thúc & Thông tin dự án** | Tổng kết hiệu quả kinh tế - xã hội, tiến độ dự kiến, logo chủ đầu tư và đơn vị tư vấn thiết kế. | 5 – 8 giây | `2D_IMAGE_CAMERA` (Fade to black / Slow zoom in logo) |

## 2. Cấu trúc dữ liệu Shot List & Storyboard

Mỗi Shot trong Storyboard được quản lý theo hợp đồng dữ liệu chuẩn:

```json
{
  "shot_id": "shot-01",
  "name": "Cảnh 01: Tổng quan dự án",
  "template_id": "project_overview",
  "asset_ids": ["asset-uuid-1"],
  "duration_sec": 6.0,
  "fps": 30,
  "camera_mode": "2D_IMAGE_CAMERA",
  "camera_motion": {
    "type": "pan_zoom",
    "start_scale": 1.0,
    "end_scale": 1.15,
    "pan_direction": "left_to_right",
    "easing": "cinematic"
  },
  "overlay_title": "DỰ ÁN ĐƯỜNG CAO TỐC BẮC - NAM",
  "subtitle_text": "Giai đoạn 1: Đoạn tuyến Km10+000 đến Km35+000",
  "narration_text": "Dự án đường cao tốc là tuyến giao thông huyết mạch kết nối các trung tâm kinh tế trọng điểm.",
  "audio_uri": null
}
```

## 3. Quy tắc kiểm duyệt Storyboard của người dùng

- Hệ thống **không bao giờ tự động khóa** nội dung hoặc ép buộc người dùng theo template AI suy đoán.
- Người dùng có thể:
  1. Thêm, xóa, thay đổi thứ tự các shot trên timeline trực quan.
  2. Gán ảnh khác vào từng shot bất cứ lúc nào.
  3. Chỉnh sửa văn bản tiêu đề hiển thị, phụ đề kỹ thuật và thuyết minh.
  4. Đổi chế độ chuyển động camera giữa `2D_IMAGE_CAMERA` (pan/zoom an toàn) và `3D_SCENE_CAMERA` khi có dữ liệu.

