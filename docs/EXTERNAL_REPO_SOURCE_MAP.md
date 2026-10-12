# Bản đồ nguồn tham khảo bên ngoài (External Repo Source Map)

Tài liệu này ghi nhận các repository, công cụ mã nguồn mở và tài liệu tham khảo được nghiên cứu cho dự án `AI-Video-` (Image-to-Cinematic-Video cho hạ tầng giao thông và công trình xây dựng Civil 3D / InfraWorks).

## 1. Bảng đối chiếu nguồn tham khảo

| Nguồn tham khảo | Mục đích / Tính năng học hỏi | Giấy phép (License) | Quyết định sử dụng trong dự án | Rủi ro / Giới hạn cần lưu ý |
|---|---|---|---|---|
| **OpenVideoStudio**<br>`https://github.com/mne03005-png/OpenVideoStudio` | - Quy trình sản xuất video có cấu trúc (script → storyboard → narration → subtitle → assembly).<br>- Checkpoints theo cảnh và resume khi lỗi.<br>- Tách biệt các giai đoạn render độc lập. | MIT | **Học hỏi kiến trúc & workflow:** Tái hiện mô hình storyboard, shot list và checkpoint rendering vào pipeline hiện có của AI-Video-. | Không phụ thuộc vào cloud services độc quyền của dự án gốc; kiểm tra codec và encoder tương thích trên máy local. |
| **AI Video Production Editor**<br>`https://github.com/LudwigKienle/ai-video-production-editor` | - Storyboard & shot list UI.<br>- Camera / lens metadata.<br>- Continuity & timeline visual cues. | GPL-3.0 (phần core) | **Chỉ tham khảo ý tưởng UX/UI và cấu trúc siêu dữ liệu shot list.** **TUYỆT ĐỐI KHÔNG copy code trực tiếp** vào codebase để tránh lây nhiễm GPL-3.0. | Giấy phép GPL-3.0 không tương thích với phân phối SaaS đóng hoặc permissive codebase nếu sao chép nguyên văn. |
| **COLMAP**<br>`https://github.com/colmap/colmap` | - Structure-from-Motion (SfM).<br>- Tái tạo camera poses và sparse point cloud từ bộ ảnh chụp overlap. | BSD-3-Clause / SIFT (patent expired, non-commercial restrictions lifted in newer releases) | **Sử dụng làm backend SfM chính thức** khi có đủ ảnh overlap và capability môi trường cho phép. | Yêu cầu binary hoặc PyCOLMAP cài đặt trên hệ thống; nếu thiếu thì fallback an toàn sang `2D_IMAGE_CAMERA`. |
| **Nerfstudio / gsplat**<br>`https://github.com/nerfstudio-project/gsplat` | - 3D Gaussian Splatting (3DGS) rasterization & rendering.<br>- Novel-view synthesis nhanh với độ phân giải cao. | Apache-2.0 | **Sử dụng làm backend 3DGS** trong Geometry Mode khi máy có GPU CUDA tương thích. | Yêu cầu NVIDIA CUDA GPU; không chạy trên CPU thuần. Cần feasibility gate và VRAM check trước khi kích hoạt. |
| **ComfyUI**<br>`https://github.com/Comfy-Org/ComfyUI` | - Adapter mở rộng cho AI video thế hệ mới (Wan2.2, HunyuanVideo, v.v.).<br>- Định dạng Workflow API JSON. | GPL-3.0 (Standalone server) | **Chỉ tích hợp qua Adapter API bên ngoài (Out-of-process HTTP/WebSocket API).** Không nhúng mã nguồn ComfyUI vào backend AI-Video-. | AI video không đảm bảo độ chính xác hình học công trình; chỉ dùng cho cảnh minh họa phụ trợ (illustration) khi người dùng duyệt. |
| **FFmpeg**<br>`https://github.com/FFmpeg/FFmpeg` | - Hợp nhất frame sequences thành MP4 H.264.<br>- Ghép âm thanh thuyết minh (narration), nhạc nền (BGM), phụ đề (subtitles) và overlay text kỹ thuật. | LGPL-2.1+ / GPL-2.0+ (tùy build flags) | **Công cụ ghép và xuất video cốt lõi.** Gọi thông qua CLI subprocess. | Cần FFmpeg binary có trong PATH hoặc chỉ định qua cấu hình `FFMPEG_PATH`. |
| **MoviePy**<br>`https://github.com/Zulko/moviepy` | - Tiện ích hỗ trợ ghép timeline, audio và text clips bằng Python khi cần kịch bản động phức tạp. | MIT | **Tham khảo / Tùy chọn bổ trợ.** Hiện tại ưu tiên pipeline FFmpeg trực tiếp để tối đa hiệu năng và kiểm soát chính xác tham số mã hóa. | Tránh tạo hai pipeline render xung đột song song. |

## 2. Nguyên tắc tích hợp mã nguồn và quyền sở hữu trí tuệ

1. **Clean Room Design:** Mọi logic xử lý nghiệp vụ, schema, models, services và API routes đều được viết mới độc lập, tuân thủ `SKILL_CANONICAL.md`.
2. **Out-of-Process Isolation:** Các thành phần có giấy phép ràng buộc cao (GPL-3.0 như ComfyUI) chỉ được giao tiếp thông qua giao thức mạng HTTP/WebSocket REST/JSON API độc lập, giữ cho backend `AI-Video-` giữ nguyên tính độc lập.
3. **No Hallucination for Technical Geometry:** Đối với các bản vẽ trắc dọc, bình đồ tuyến, mặt cắt ngang của Civil 3D / InfraWorks, ưu tiên bảo toàn tuyệt đối hình học nguồn qua `2D_IMAGE_CAMERA` và `3D_SCENE_CAMERA`.

