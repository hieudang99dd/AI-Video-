# Hướng Dẫn Cấu Hình GPU, CUDA & Моdule AI Nâng Cao (GPU_SETUP.md)

Tài liệu này hướng dẫn cấu hình GPU NVIDIA, CUDA, PyTorch và cách kích hoạt các mô-đun AI tùy chọn (**DUSt3R**, **MoVerse**, **Wan2.2**) theo đúng yêu cầu kiến trúc: **không tự động tải các mô hình hàng chục GB trong lúc cài đặt cơ bản** và **kiểm tra VRAM/License trước khi khởi chạy**.

---

## 1. Kiểm Tra Phần Cứng GPU Hiện Tại

Hệ thống tự động thăm dò phần cứng GPU qua hai lớp:
1. `torch.cuda` (nếu đã cài đặt PyTorch CUDA).
2. `nvidia-smi` (hoạt động ngay cả khi chỉ mới cài môi trường Python cơ bản).

Trên máy trạm phát triển hiện tại, hệ thống ghi nhận:
- **GPU:** `NVIDIA GeForce RTX 5070 Ti`
- **VRAM:** `16,303 MB (~16 GB VRAM)`
- **Driver:** `576.88`

Bạn có thể kiểm tra trực tiếp qua API:
```powershell
curl http://127.0.0.1:8000/api/v1/capabilities
curl http://127.0.0.1:8000/api/v1/ai-modules/status
```

---

## 2. Yêu Cầu VRAM Theo Từng Chế Độ Vận Hành

| Chế độ / Моdule | VRAM Tối Thiểu | VRAM Khuyến Nghị | Ghi chú |
|---|---|---|---|
| **Core Pipeline (2.5D + OpenCV + FFmpeg H.264)** | 0 GB (CPU) | 4 GB | Chạy mượt mà trên mọi máy tính, không yêu cầu GPU rời. |
| **COLMAP Dense MVS + Blender EEVEE/Cycles** | 6 GB | 12 GB+ | Tăng tốc độ dựng Point Cloud và Render 3D. |
| **DUSt3R (Multi-view 3D Reconstruction)** | 8 GB | 12 GB+ | Cần bật cờ `IVB_ALLOW_NON_COMMERCIAL_MODELS=true`. |
| **MoVerse (Novel View Synthesis)** | 12 GB | 16 GB+ | Sinh góc nhìn mới dọc theo quỹ đạo camera. |
| **Wan2.2-TI2V-5B (Video Enhancement 720p)** | 12 GB | 16 GB – 24 GB | Tương thích hoàn hảo với **RTX 5070 Ti 16GB VRAM** (sử dụng `bfloat16` + CPU Offload). |
| **Wan2.2-A14B / I2V-A14B** | 24 GB+ | 40 GB – 80 GB | Chỉ dành cho máy chủ GPU A100/H100 hoặc đa GPU. |

---

## 3. Cài Đặt PyTorch với CUDA (Tùy Chọn Khi Cần Chạy AI Trên GPU Nội Bộ)

Mặc định dự án không ép cài đặt PyTorch CUDA (~2.5 GB) để giữ thời gian cài đặt nhanh. Khi bạn muốn chạy trực tiếp `DUSt3R` hoặc `Wan2.2-TI2V-5B` trên GPU NVIDIA:

```powershell
.\.venv\Scripts\Activate.ps1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install diffusers transformers accelerate safetensors
```

---

## 4. Tải Trọng Số Mô Hình (Model Weights) Thủ Công Có Kiểm Soát

Tất cả trọng số mô hình được quản lý tập trung tại thư mục `IVB_MODELS_ROOT` (mặc định: `./models`).

### 4.1. Kích Hoạt `Wan2.2-TI2V-5B` (Apache-2.0)

1. Tải trọng số về thư mục `./models/Wan2.2-TI2V-5B` bằng `huggingface-cli`:
   ```powershell
   pip install huggingface_hub
   huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./models/Wan2.2-TI2V-5B
   ```
2. Bật trong `.env`:
   ```env
   IVB_MODELS_ROOT=./models
   IVB_WAN_ENABLED=true
   IVB_WAN_MODEL_ID=Wan-AI/Wan2.2-TI2V-5B
   ```

### 4.2. Kích Hoạt `MoVerse` (Apache-2.0)

1. Đặt checkpoint vào `./models/moverse` hoặc chạy MoVerse dưới dạng Inference Microservice độc lập.
2. Cấu hình trong `.env`:
   ```env
   IVB_MOVERSE_ENABLED=true
   IVB_MOVERSE_ENDPOINT=http://127.0.0.1:8090/infer
   ```

### 4.3. Kích Hoạt `DUSt3R` (CC BY-NC-SA 4.0 — Chỉ Dùng Cho Nghiên Cứu / Phi Thương Mại)

> **Cảnh báo bản quyền:** Trọng số `DUSt3R` sử dụng giấy phép **CC BY-NC-SA 4.0** (Phi thương mại). Hệ thống sẽ tự động **khóa** mô-đun này trong môi trường thương mại trừ khi người vận hành xác nhận rõ ràng.

1. Đặt checkpoint vào `./models/dust3r`.
2. Bật đồng thời cả hai biến môi trường trong `.env`:
   ```env
   IVB_DUST3R_ENABLED=true
   IVB_ALLOW_NON_COMMERCIAL_MODELS=true
   ```
