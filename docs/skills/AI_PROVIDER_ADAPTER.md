# Bộ điều hợp AI tùy chọn (AI Provider Adapter)

Tài liệu này đặc tả thiết kế và cơ chế hoạt động của `AIProviderAdapter` dùng để kết nối với các hệ thống AI Video thế hệ mới (ComfyUI / Wan2.2 / HunyuanVideo) như một module mở rộng độc lập, không bắt buộc.

## 1. Nguyên tắc cốt lõi về tích hợp AI

1. **Hoàn toàn tùy chọn (Strictly Optional):** Ứng dụng phải hoạt động trọn vẹn, xuất được video MP4 hoàn chỉnh bằng CPU/FFmpeg fallback mà không cần cài đặt hoặc khởi chạy bất kỳ AI model nào.
2. **Không tự ý phát sinh chi phí:** Không gọi API cloud trả phí hoặc dịch vụ GPU bên thứ ba nếu người dùng chưa cấu hình và xác nhận rõ ràng.
3. **Không tự động tải model khổng lồ:** Không tự động tải các checkpoint hàng chục Gigabytes về máy người dùng làm tắc nghẽn tài nguyên và băng thông mạng.
4. **Cách ly mạng (Network Boundary Isolation):** Tương tác với ComfyUI độc lập qua API REST/WebSocket, tuyệt đối không gộp mã nguồn GPL-3.0 vào lõi hệ thống.

## 2. Giao diện Adapter (Contract)

```python
class AIProviderAdapter:
    """Out-of-process adapter for generative AI video providers."""

    def is_available(self) -> dict:
        """Kiểm tra tính sẵn sàng của endpoint AI (URL, health, model list)."""
        ...

    def generate_clip(
        self,
        image_path: Path,
        prompt: str,
        duration_sec: float,
        fps: int,
        output_path: Path,
        progress_callback: Callable[[float, str], None],
        cancel_callback: Callable[[], bool],
    ) -> dict:
        """Gửi yêu cầu sinh video sang ComfyUI / Model server."""
        ...
```

## 3. Cơ chế xử lý sự cố & Fallback

- **Timeout:** Mỗi yêu cầu AI clip có giới hạn thời gian chạy tối đa (mặc định 180 giây). Nếu quá thời gian, job tự hủy kết nối để giải phóng tài nguyên.
- **Lỗi kết nối hoặc OOM:** Nếu ComfyUI sập hoặc GPU hết VRAM (CUDA Out Of Memory), hệ thống ghi log chi tiết lỗi vào `job.provenance["ai_error"]` và tự động chuyển sang chế độ an toàn `2D_IMAGE_CAMERA` để bảo đảm người dùng vẫn nhận được video đầu ra.
