# Rà soát giấy phép mã nguồn mở (Open Source License Audit)

Tài liệu này đánh giá tính tương thích giấy phép của toàn bộ các thư viện, công cụ, model weights và dependencies sử dụng trong dự án `AI-Video-`.

## 1. Bảng rà soát chi tiết

| Gói / Công cụ / Model | Phiên bản khảo sát | Giấy phép Code | Giấy phép Model / Weights | Quyền thương mại (Commercial) | Tái phân phối (Redistribution) | Yêu cầu Attribution / Notice | Quyết định sử dụng |
|---|---|---|---|---|---|---|---|
| **FastAPI** | 0.115+ | MIT | N/A | Có | Có | Có (giữ copyright notice) | **Dùng trực tiếp** làm web framework backend. |
| **SQLAlchemy** | 2.0+ | MIT | N/A | Có | Có | Có (giữ MIT notice) | **Dùng trực tiếp** làm ORM và quản lý cơ sở dữ liệu SQLite / PostgreSQL. |
| **Pydantic** | 2.9+ | MIT | N/A | Có | Có | Có | **Dùng trực tiếp** cho schemas, data validation và settings. |
| **Pillow (PIL)** | 10.4+ | HPND | N/A | Có | Có | Có (giữ license text) | **Dùng trực tiếp** cho xử lý ảnh, crop, zoom, pad và phân tích kích thước. |
| **NumPy** | 1.26+ | BSD-3-Clause | N/A | Có | Có | Có (giữ BSD license) | **Dùng trực tiếp** cho tính toán ma trận, quaternion, vector toán học camera. |
| **OpenCV (opencv-python-headless)** | 4.10+ | Apache-2.0 | N/A | Có | Có | Có | **Dùng trực tiếp** (optional) cho Laplacian variance đánh giá độ nét ảnh. |
| **Next.js** | 15 / 16 | MIT | N/A | Có | Có | Có | **Dùng trực tiếp** cho Web Frontend App Router. |
| **React** | 19 | MIT | N/A | Có | Có | Có | **Dùng trực tiếp** cho UI component rendering. |
| **FFmpeg (CLI binary)** | 6.x / 7.x | LGPL-2.1+ (hoặc GPL nếu build kèm x264/x265) | N/A | Có (với điều kiện tuân thủ LGPL/GPL khi phân phối binary) | Chỉ phân phối nhị phân nếu cấp kèm mã nguồn FFmpeg theo GPL/LGPL | Có (hiển thị banner FFmpeg trong documentation) | **Gọi qua Subprocess CLI riêng biệt**, không nhúng thư viện tĩnh vào binary ứng dụng. |
| **COLMAP** | 3.8+ | BSD-3-Clause | N/A | Có | Có | Có | **Gọi qua Subprocess CLI / Backend Adapter**, chỉ kích hoạt khi máy có cài đặt. |
| **gsplat / Nerfstudio** | 1.1+ | Apache-2.0 | N/A | Có | Có | Có | **Dùng qua backend adapter** cho huấn luyện và render Gaussian Splatting khi có GPU CUDA. |
| **ComfyUI API** | 0.2+ | GPL-3.0 | N/A | Có (khi chạy như dịch vụ mạng tách biệt) | Không gộp code vào cùng repo | Có | **Gọi qua Adapter HTTP/WebSocket độc lập**, người dùng tự lưu trữ hoặc kết nối server riêng. |
| **Wan2.2 / HunyuanVideo (AI Video Models)** | 14B / 72B | Apache-2.0 / Custom Open Weights | Apache-2.0 hoặc Open Model License (theo từng nhà phát hành) | Cần kiểm tra cụ thể từng checkpoint | Theo điều khoản từng model | Có | **Chỉ kết nối qua adapter khi người dùng yêu cầu rõ ràng**, không tự động tải model vào máy người dùng. |

## 2. Kết luận và quy tắc tuân thủ pháp lý

1. **Không sao chép mã nguồn GPL-3.0 vào core codebase:** Mã nguồn trong `apps/api`, `apps/web` và `packages/*` tuân thủ các giấy phép thoáng (Permissive: MIT/Apache-2.0). Mọi tương tác với công cụ GPL như ComfyUI đều qua API giao thức mạng (Network Service Boundary).
2. **FFmpeg Compliance:** Hệ thống sử dụng FFmpeg như một tiến trình độc lập (`subprocess.run`), truyền file qua hệ thống tệp và stdout/stderr, hoàn toàn đáp ứng điều kiện giấy phép LGPL/GPL mà không ảnh hưởng tới bản quyền mã nguồn của dự án.
3. **Model Weights Disclaimer:** Dự án không lưu trữ sẵn hay bundle các checkpoint trọng số model AI nặng hoặc có điều khoản hạn chế thương mại. Người dùng có toàn quyền cấu hình adapter nếu có nhu cầu.

