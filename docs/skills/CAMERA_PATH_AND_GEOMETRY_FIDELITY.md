# Quỹ đạo Camera và Bảo toàn Hình học (Camera Path & Geometry Fidelity)

Tài liệu này đặc tả 3 chế độ Camera, các ngưỡng ràng buộc kỹ thuật và cơ chế kiểm duyệt chuyển động (Path Validation Gate) nhằm bảo đảm không làm biến dạng công trình xây dựng.

## 1. Ba chế độ Camera bắt buộc

Hệ thống phân định rạch ròi 3 chế độ Camera và khai báo minh bạch tới người dùng:

### 1. `2D_IMAGE_CAMERA` (Camera 2D trên nguồn ảnh tĩnh)
- **Bản chất:** Chuyển động crop, pan, zoom (Ken Burns nâng cao) trên một hoặc nhiều ảnh nguồn chất lượng cao.
- **Ràng buộc an toàn:**
  - Tỷ lệ zoom tối đa: $1.00 \times \le \text{scale} \le 1.35 \times$ (tránh hiện tượng vỡ hạt điểm ảnh hoặc làm biến dạng tỷ lệ bản vẽ).
  - Vận tốc pan tối đa: không vượt quá $25\%$ chiều rộng ảnh trên 1 giây.
  - Phép xoay: không thực hiện xoay phối cảnh giả tạo; chỉ tịnh tiến $X, Y$ hoặc zoom mượt mà với easing `cinematic` ($t^2(3-2t)$).
  - Nghiêm cấm gán nhãn chế độ này là "Camera bay 3D".

### 2. `3D_SCENE_CAMERA` (Camera 3D trong không gian thực)
- **Bản chất:** Camera tự do di chuyển trong không gian 3D được tái tạo từ Structure-from-Motion (COLMAP) hoặc mô hình 3DGS/Mesh.
- **Ràng buộc hình học:**
  - Hướng xoay camera: Bắt buộc sử dụng Quaternion và nội suy Spherical Linear Interpolation (SLERP) với định dạng chuẩn `[x, y, z, w]`. Tuyệt đối không nội suy trực tiếp góc Euler để tránh hiện tượng khóa góc (Gimbal Lock).
  - Vận tốc góc tối đa: $\le 45^\circ/\text{giây}$.
  - Vận tốc di chuyển tối đa: $\le 5.0\text{ m/giây}$ (tùy thuộc vào tỷ lệ scene).
  - Khoảng cách an toàn (Clearance): Kiểm tra va chạm với đám mây điểm (`PointCloudProxy`). Nếu camera đi quá gần bề mặt công trình ($< 0.2\text{m}$), hệ thống từ chối render và yêu cầu nắn chỉnh keyframe.

### 3. `AI_VIDEO_CAMERA` (Camera AI tùy chọn)
- **Bản chất:** Video do mô hình AI khuếch tán tạo ra (như Wan2.2 / Hunyuan qua ComfyUI).
- **Ràng buộc pháp lý & kỹ thuật:**
  - Khai báo rõ ràng đây là hình ảnh minh họa nghệ thuật (concept visualization), không có giá trị nghiệm thu kỹ thuật hoặc kiểm tra trắc địa.
  - Phải có sự phê duyệt rõ ràng từ người dùng trước khi áp dụng vào cảnh.

## 2. Tiêu chí kiểm duyệt đường bay Camera (Path Validation Gate)

Trước khi gửi job render chính thức sang worker, `PathValidator` tự động chấm điểm đường camera từ $0.0$ đến $1.0$:

$$\text{Score} = w_s \cdot S_{\text{smooth}} + w_c \cdot S_{\text{clearance}} + w_v \cdot S_{\text{view}} + w_g \cdot S_{\text{geometry}}$$

- **Ngưỡng tối thiểu:** $\text{Score} \ge 0.65$.
- Nếu vi phạm (va chạm vật thể, đổi tiêu cự đột ngột $> 35\%$, vận tốc góc quá nhanh):
  1. Tự động đề xuất nắn keyframe.
  2. Báo lý do cụ thể trong `rejection_reasons`.
  3. Tự động fallback về `2D_IMAGE_CAMERA` an toàn nếu người dùng muốn xuất video ngay lập tức.
