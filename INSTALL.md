# Hướng Dẫn Cài Đặt (INSTALL.md)

Tài liệu này hướng dẫn cài đặt đầy đủ hệ thống **AI-Video: Hệ Thống Tự Động Tạo Video Hạ Tầng Giao Thông (Civil 3D / InfraWorks)** theo hai chế độ vận hành:

1. **Chế độ Cơ Bản (Core Pipeline - Bắt buộc chạy được ngay trên mọi máy tính)**
2. **Chế độ Nâng Cao (3D Reconstruction COLMAP / Blender Headless / AI GPU Models)**

---

## 1. Yêu Cầu Hệ Thống

| Thành phần | Chế độ Cơ Bản (Core Pipeline) | Chế độ Nâng Cao (Full 3D + AI GPU) |
|---|---|---|
| **Hệ điều hành** | Windows 10/11 (64-bit) hoặc Ubuntu 22.04 LTS | Windows 11 / Ubuntu 22.04 LTS |
| **Python** | Python `3.11+` (`3.11` – `3.13`) | Python `3.11+` |
| **RAM** | Tối thiểu 8 GB (Khuyến nghị 16 GB) | 32 GB+ |
| **GPU** | Không bắt buộc (Chạy CPU / WebGL) | NVIDIA RTX 12GB+ VRAM (Đã kiểm thử trên **RTX 5070 Ti 16GB**) |
| **FFmpeg** | Tự động tích hợp sẵn qua `imageio-ffmpeg` | FFmpeg hệ thống hoặc `imageio-ffmpeg` (Hỗ trợ NVENC / libx264) |
| **Dung lượng đĩa** | ~2 GB trống | 40 GB+ trống (Nếu tải thêm trọng số AI Wan2.2 / MoVerse) |

---

## 2. Cài Đặt Chế Độ Cơ Bản (Core Pipeline)

Chế độ Cơ Bản bao gồm đầy đủ 9 bước pipeline:
`IMAGE INGESTION → IMAGE QUALITY ANALYSIS → RECONSTRUCTION (Fallback 2.5D/Ordered Path) → SCENE REPRESENTATION → CAMERA PLANNER (10 Twinmotion Presets + Catmull-Rom + SLERP) → 3D RENDER ENGINE (Blender Script Generator + OpenCV Renderer) → AI QC → VIDEO COMPOSER → MP4 EXPORT (H.264)`.

### Bước 2.1: Clone Repository và Tạo Môi Trường Ảo (Virtual Environment)

**Trên Windows (PowerShell):**
```powershell
git clone https://github.com/hieudang99dd/AI-Video-.git
cd AI-Video-
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Trên Linux / Ubuntu (Bash):**
```bash
git clone https://github.com/hieudang99dd/AI-Video-.git
cd AI-Video-
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 2.2: Cài Đặt Dependencies Backend & Xử Lý Hình Ảnh / Video

> **Lưu ý quan trọng:** Quá trình `pip install` dưới đây **không tự động tải các model AI nặng hàng chục GB**. Hệ thống chỉ cài đặt các thư viện cốt lõi (`FastAPI`, `SQLAlchemy`, `OpenCV`, `Pillow`, `NumPy`, `imageio-ffmpeg`) để đảm bảo khởi chạy tức thì.

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".\apps\api[dev]"
```

### Bước 2.3: Kiểm Tra Capabilities Hệ Thống

Khởi động FastAPI server:
```powershell
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
```

Kiểm tra trạng thái phần cứng, FFmpeg, COLMAP, Blender và các module AI:
```powershell
curl http://127.0.0.1:8000/api/v1/capabilities
```

Truy cập giao diện ứng dụng:
- Giao diện Web Studio 4 Bước đầy đủ: Mở trực tiếp file `index.html` hoặc truy cập `http://127.0.0.1:8000/`

### Bước 2.4: Chạy Bộ Kiểm Thử Tự Động (Unit + Integration + E2E Smoke Tests)

```powershell
.\.venv\Scripts\pytest.exe -v
```

---

## 3. Cài Đặt Chế Độ Nâng Cao (Tùy Chọn: COLMAP, Blender, AI GPU)

Hệ thống thiết kế theo kiến trúc **Capability-Gated Adapter**. Khi bạn cài thêm các công cụ dưới đây, hệ thống sẽ tự động phát hiện hoặc kích hoạt thông qua biến môi trường (`.env`).

### 3.1. Cài Đặt COLMAP (Khôi Phục Cảnh 3D Thực Sự - Chế Độ A: `A_RECONSTRUCTED_3D`)

- **Windows:** Tải bản thực thi COLMAP (CUDA hoặc Nocuda) từ [COLMAP Releases](https://github.com/colmap/colmap/releases), giải nén và thêm thư mục chứa `colmap.exe` vào `PATH` hoặc khai báo trong `.env`:
  ```env
  IVB_COLMAP_PATH=C:\tools\colmap\bin\colmap.exe
  ```
- **Ubuntu:**
  ```bash
  sudo apt-get update && sudo apt-get install -y colmap
  ```

### 3.2. Cài Đặt Blender Headless (Render 3D Ngoại Tuyến Chất Lượng Cao)

Ngay cả khi chưa cài Blender, hệ thống luôn xuất sẵn tệp kịch bản Python 3D (`shot_{id}_blender.py`) và quỹ đạo nội suy (`shot_{id}_camera_trajectory.json`). Nếu cài đặt Blender, hệ thống sẽ tự động gọi `blender -b -P` để kết xuất 3D:

- **Windows:** Cài đặt Blender 3.6 LTS hoặc 4.x từ [blender.org](https://www.blender.org/download/) và cấu hình:
  ```env
  IVB_BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
  ```
- **Ubuntu:**
  ```bash
  sudo apt-get install -y blender
  ```

### 3.3. Cấu Hình Biến Môi Trường (`.env`)

Tạo file `.env` tại thư mục gốc của dự án nếu cần tùy chỉnh nâng cao:

```env
IVB_APP_ENV=development
IVB_STORAGE_ROOT=./data
IVB_DATABASE_URL=sqlite:///./data/app.db
IVB_FFMPEG_PATH=ffmpeg
IVB_COLMAP_PATH=colmap
IVB_BLENDER_PATH=blender

# Cấu hình AI nâng cao (Mặc định tắt để đảm bảo nhẹ và an toàn bản quyền)
IVB_MODELS_ROOT=./models
IVB_WAN_ENABLED=false
IVB_WAN_MODEL_ID=Wan-AI/Wan2.2-TI2V-5B
IVB_MOVERSE_ENABLED=false
IVB_DUST3R_ENABLED=false
IVB_ALLOW_NON_COMMERCIAL_MODELS=false
```
