---
name: image-to-cinematic-video
description: >
  Nguồn chuẩn duy nhất để build, sửa, kiểm thử, vận hành và mở rộng sản phẩm
  Image-to-Cinematic-Video: biến ảnh chụp công trình/nội-ngoại thất thành video
  chuyển động camera kiểu Twinmotion. Ưu tiên Geometry-first với SfM và 3D
  reconstruction/3D Gaussian Splatting khi dữ liệu đủ; fallback an toàn sang
  2.5D hoặc cut/transition khi dữ liệu không đủ. Sản phẩm đích là Web SaaS có
  Hybrid GPU: dùng Local GPU Agent của chính user hoặc Cloud GPU Worker, nhưng
  Hybrid GPU chỉ được triển khai sau khi Core Engine đã vượt quality gate.
version: 4.0.0
language: vi
source_of_truth: true
---

# SKILL: Image-to-Cinematic-Video — Canonical Source


## 0. Cách dùng và thứ tự ưu tiên của file này

Đây là **nguồn chuẩn duy nhất (single source of truth)** cho project.

Không có tài liệu `` bắt buộc đi kèm. Nếu repo có tài liệu cũ mâu thuẫn
với file này, ưu tiên theo thứ tự:

1. Yêu cầu rõ ràng mới nhất của user/product owner.
2. Các nguyên tắc bất biến và phase gate trong file này.
3. Data/API contract trong file này.
4. Implementation hiện tại trong repo.
5. Tài liệu cũ khác.

Khi sửa kiến trúc, API, data model, job state, execution mode hoặc Definition of
Done, phải cập nhật file này trong cùng thay đổi để tránh drift.

Nếu task chỉ là một thay đổi nhỏ, agent không cần đọc lại mọi section; dùng mục
lục/heading để đọc đúng phần liên quan. Nhưng khi thay đổi cross-cutting concern
như render pipeline, worker protocol, storage, auth, billing hoặc Hybrid GPU,
phải kiểm tra tất cả section có liên quan trước khi code.

### 0.0. Các tài liệu hướng dẫn triển khai bổ trợ (Implementation Guides)

Các tài liệu bổ trợ hướng dẫn triển khai chi tiết cho domain video hạ tầng kỹ thuật (không thay thế đặc tả chuẩn này):

- [`docs/EXTERNAL_REPO_SOURCE_MAP.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/EXTERNAL_REPO_SOURCE_MAP.md): Bản đồ nguồn tham khảo và quyết định tích hợp mã nguồn.
- [`docs/skills/OPEN_SOURCE_LICENSE_AUDIT.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/skills/OPEN_SOURCE_LICENSE_AUDIT.md): Bảng rà soát giấy phép mã nguồn mở và model weights.
- [`docs/skills/INFRASTRUCTURE_VIDEO_WORKFLOW.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/skills/INFRASTRUCTURE_VIDEO_WORKFLOW.md): Quy trình sản xuất video từ ảnh xuất Civil 3D / InfraWorks.
- [`docs/skills/SCENE_PLANNING_AND_STORYBOARD.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/skills/SCENE_PLANNING_AND_STORYBOARD.md): 8 Template phân cảnh chuẩn và cấu trúc Storyboard.
- [`docs/skills/CAMERA_PATH_AND_GEOMETRY_FIDELITY.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/skills/CAMERA_PATH_AND_GEOMETRY_FIDELITY.md): 3 Chế độ Camera và thuật toán bảo toàn hình học kỹ thuật.
- [`docs/skills/RENDER_AND_EXPORT.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/skills/RENDER_AND_EXPORT.md): Pipeline Render, lồng tiếng, phụ đề, nhạc nền và Quality Control.
- [`docs/skills/AI_PROVIDER_ADAPTER.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/skills/AI_PROVIDER_ADAPTER.md): Bộ điều hợp AI Video tùy chọn (ComfyUI / Wan2.2).
- [`docs/skills/HARDWARE_AND_BENCHMARKS.md`](file:///c:/Users/hieu.dv/Downloads/image-to-cinematic-video-phase1/image-to-cinematic-video/docs/skills/HARDWARE_AND_BENCHMARKS.md): Ma trận Fallback phần cứng CPU/GPU và chỉ số hiệu năng.

### Quy ước về ngưỡng số liệu

Mọi threshold trong file này như:

- geometry confidence
- minimum registered ratio
- max angular velocity
- min render score
- artifact risk
- VRAM requirement
- retry count

đều là **giá trị khởi đầu để hệ thống chạy được**, không phải chân lý đã được
kiểm chứng. Chúng phải:

- nằm trong config;
- có telemetry;
- được calibrate bằng dataset thực;
- không hard-code rải rác trong code.

### Quy mô dự án

Đây là sản phẩm R&D gồm computer vision, 3D reconstruction, camera planning,
novel-view rendering, video pipeline, distributed workers và ở Phase 2 có thêm
device fleet/Hybrid GPU. Không được coi đây là một feature nhỏ hoặc cố "build
xong toàn bộ" trong một vertical slice.

---

## 0.1. Phân kỳ bắt buộc

### Phase 0 — Technical Feasibility Spike

Mục tiêu duy nhất: chứng minh lõi công nghệ trước khi xây SaaS lớn.

Vertical slice:

```text
Images
  -> Camera reconstruction
  -> Scene representation
  -> 2-3 camera keyframes
  -> safe camera path
  -> 5-second preview
  -> MP4
```

Tối thiểu phải thử trên:

- exterior có overlap tốt;
- interior có overlap tốt;
- sparse/khó để xác nhận fallback;
- single image để xác nhận 2.5D;
- disconnected scenes để xác nhận cut/transition.

**Không xây Hybrid GPU, billing, team collaboration hoặc autoscaling trong Phase 0.**

### Phase 1 — Core Engine

Sau khi Phase 0 pass, xây end-to-end product core:

```text
Upload
 -> Analyze
 -> Scene grouping
 -> Reconstruction / fallback
 -> Storyboard
 -> Camera editor
 -> Preview
 -> Render
 -> MP4
```

Phase 1 chạy trên **một worker execution target duy nhất** (máy dev hoặc một
cloud GPU cố định). Chưa cần Local GPU Agent/Device Registry/Hybrid Router.

### Phase 2 — Hybrid GPU

Chỉ bắt đầu khi Phase 1 vượt exit gate.

Thêm:

- Local GPU Agent;
- Device Registry;
- pairing/revoke;
- worker capability negotiation;
- Hybrid Job Router;
- My GPU / Cloud GPU / Auto;
- cloud cost confirmation;
- worker reconnect/recovery.

### Phase 3 — Product Intelligence

Thêm sau khi pipeline cơ bản ổn định:

- Auto Director;
- automatic shot selection;
- path optimization;
- quality prediction;
- temporal refinement nâng cao;
- optional beat/music assistance.

### Phase 4 — Commercial Scale

Thêm khi có nhu cầu vận hành thật:

- billing;
- credits/subscription;
- teams/organizations;
- cloud autoscaling;
- observability/analytics hoàn chỉnh;
- quotas/rate limiting theo plan;
- SLO/SLA;
- backup/DR.

### Không trộn phase

Không được đưa Phase 2 vào vertical slice đầu tiên chỉ vì kiến trúc đích có
Hybrid GPU. Trước hết phải chứng minh engine tạo video tốt.

---

## 0.2. Exit gate giữa các phase

### Gate Phase 0 -> Phase 1

Chỉ pass khi:

- ít nhất một dataset exterior và một dataset interior dựng được scene;
- camera path 5 giây render end-to-end thành MP4;
- start/end view tương thích với source view;
- không có lỗi kiến trúc nghiêm trọng trong vùng đã quan sát;
- fallback hoạt động trên single-image và disconnected-scene cases;
- pipeline có log thời gian, VRAM/RAM và failure reason.

### Gate Phase 1 -> Phase 2

Không bắt đầu Hybrid GPU nếu chưa đạt tối thiểu:

- 20 render liên tiếp trên golden datasets không crash process;
- job cancel/retry hoạt động;
- GPU OOM không làm chết worker pool;
- camera path validation chạy trước final render;
- output/project state persistent sau restart;
- reconstruction/render config có version;
- core API/job contract đủ ổn định để worker remote dùng chung.

Các tỷ lệ thành công mục tiêu cụ thể phải được calibrate từ dataset thật; không
đặt một con số đẹp rồi coi là bằng chứng chất lượng.

### Gate Phase 2 -> Phase 3/4

Hybrid GPU chỉ được coi là ổn khi:

- Local Agent pair/revoke/reconnect ổn;
- local/cloud dùng cùng worker protocol;
- paid cloud không chạy nếu chưa được xác nhận;
- device isolation và security audit pass;
- worker mất mạng không corrupt project;
- telemetry xác định được cost/time theo execution target.

---

## 0.3. Non-goals trước khi Core Engine ổn định

Không ưu tiên các mục sau trong Phase 0-1 trừ khi user yêu cầu riêng:

- BIM/CAD authoring đầy đủ;
- FBX/USD/DCC editor;
- character animation;
- weather simulation phức tạp;
- day/night generative relighting toàn cảnh;
- AI people/vehicle generation;
- full music editor;
- GPU marketplace giữa các user;
- collaboration real-time kiểu Figma;
- mobile native app;
- plugin ecosystem;
- arbitrary scene editing như một DCC tool.

Mục tiêu đầu tiên là **ảnh -> camera-consistent video giữ fidelity kiến trúc**.

---

## 0.4. Gate về license trước khi khóa tech stack

Trước khi kiến trúc phụ thuộc sâu vào:

- COLMAP/PyCOLMAP;
- gsplat/Nerfstudio hoặc implementation 3DGS khác;
- pretrained depth/refinement models;
- codecs/binaries phân phối cùng app;
- model/checkpoint bên thứ ba;

phải kiểm tra license có phù hợp mục đích thương mại và cách phân phối hay không.

Ghi lại:

```text
dependency
version
license
commercial_use
redistribution
model_weights_terms
attribution_required
decision
```

Không để license audit đến cuối dự án.

---

## 0.5. Measure before optimize

Không tối ưu GPU/cost theo cảm tính.

Mỗi stage quan trọng phải đo tối thiểu:

- wall-clock time;
- CPU/GPU utilization;
- peak VRAM;
- peak RAM;
- disk/cache usage;
- registered image ratio;
- reconstruction error/quality proxy;
- render FPS;
- artifact/quality score;
- retry/failure reason;
- bytes upload/download.

Chỉ sau khi có benchmark mới quyết định:

- GPU class mặc định;
- preview/final preset;
- cloud pricing;
- cache policy;
- autoscaling;
- threshold quality.

---

## 1. Mục tiêu

Xây dựng một sản phẩm hoàn chỉnh cho phép người dùng:

1. Tạo project.
2. Upload một hoặc nhiều ảnh của một dự án bất kỳ.
3. Hệ thống tự phân nhóm ảnh theo không gian/cảnh.
4. Ước lượng camera pose cho từng ảnh.
5. Tái tạo scene 3D hoặc 2.5D từ ảnh.
6. Biến ảnh thành camera keyframe.
7. Tự tạo hoặc cho phép chỉnh camera path.
8. Preview chuyển động camera.
9. Render các novel view trung gian.
10. Tự xử lý vùng thiếu, rung/flicker, artifact và upscale.
11. Xuất video MP4/MOV.
12. Cho phép dựng nhiều shot rồi ghép thành một video cinematic.

Trải nghiệm người dùng phải gần với logic của Twinmotion:

`Image/View -> Camera Keyframe -> Camera Path -> Timing/Easing -> Render -> Video`

Khác biệt quan trọng: vì đầu vào chỉ là ảnh 2D, hệ thống phải có thêm tầng:

`Images -> Camera Estimation -> Scene Reconstruction -> Novel View Rendering`

---


# 1.1. Kiến trúc sản phẩm đích — Hybrid GPU (triển khai từ Phase 2)

Sản phẩm đích phải là **Web SaaS**, không phải desktop app thuần. Tuy nhiên Phase 0-1 có thể chạy trên một worker duy nhất để chứng minh Core Engine trước.

Người dùng mở một URL duy nhất:

```text
https://app.example.com
```

Sau khi đăng nhập, hệ thống phải cho phép chọn nơi xử lý:

```text
Execution Mode

○ Auto
○ My GPU
○ Cloud GPU
```

Ba mode có ý nghĩa:

## Auto

- Nếu có Local GPU Agent đang online và GPU đủ điều kiện -> ưu tiên Local GPU.
- Nếu không có Local GPU phù hợp -> đề xuất Cloud GPU.
- Nếu Cloud GPU phát sinh phí -> phải hiển thị ước tính và yêu cầu user xác nhận trước khi thuê.
- Không được tự ý phát sinh chi phí cloud mà không có xác nhận của user.

## My GPU

- Chạy job trên một máy đã được pair với tài khoản.
- Máy đó có thể là máy đang mở trình duyệt hoặc một máy khác cùng tài khoản.
- Ví dụ: user ở nhà vẫn có thể chọn PC công ty nếu PC công ty đang online và Agent đang chạy.
- Website không được giả định GPU local là GPU của browser device.

## Cloud GPU

- Chạy job trên Cloud GPU Worker.
- Backend/Job Router chọn worker đáp ứng yêu cầu VRAM, CUDA, model/runtime và SLA.
- Cloud worker có thể scale từ 0 lên N worker theo queue.

---

# 1.2. Không được phụ thuộc vào laptop development

Laptop của developer chỉ dùng để:

- viết code
- chạy frontend/backend local
- test API
- test UI
- test CPU path
- test mock worker
- test 2.5D nhẹ

Production phải chạy độc lập trên server/cloud.

Không được:

- hardcode đường dẫn local
- hardcode localhost trong source
- hardcode GPU là local CUDA
- lưu dữ liệu production trên laptop developer
- yêu cầu laptop developer phải bật để website hoạt động

---

# 1.3. Browser không phải là GPU worker chính

Web browser chỉ chịu trách nhiệm:

- UI
- upload
- project state
- timeline
- camera path editor
- lightweight preview
- local device discovery qua backend state
- nhận progress qua SSE/WebSocket

Không được thiết kế production pipeline yêu cầu browser trực tiếp chạy:

- COLMAP full
- 3DGS training
- CUDA kernels
- PyTorch model lớn
- final rendering dài
- arbitrary native binaries

WebGPU có thể dùng cho preview hoặc tính toán nhẹ, nhưng không thay thế Local GPU Agent trong kiến trúc chính.

---


# 2. Product contract

## 2.1 Input hỗ trợ

Tối thiểu phải hỗ trợ:

- JPG
- JPEG
- PNG
- WEBP

Khuyến nghị:

- 3–100 ảnh mỗi scene.
- 1080p trở lên.
- Ảnh có overlap từ 30% trở lên cho Geometry Mode.
- Hỗ trợ cả ảnh exterior và interior.
- Ảnh có EXIF thì khai thác EXIF nhưng không phụ thuộc tuyệt đối vào EXIF.

Có thể nhận:

- 1 ảnh.
- Một nhóm ảnh cùng phòng.
- Một nhóm ảnh quanh một công trình.
- Nhiều nhóm ảnh không liên tục về không gian.

Không được giả định mọi ảnh đều thuộc cùng một scene.

---

## 2.2 Output

Tối thiểu:

- MP4 H.264
- 1080p
- 24/25/30 fps
- video preview chất lượng thấp
- video final chất lượng cao

Khuyến nghị thêm:

- MOV
- H.265
- 4K
- PNG frame sequence
- ProRes nếu FFmpeg build hỗ trợ
- alpha sequence khi renderer hỗ trợ

---

# 3. Ba chế độ dựng video bắt buộc

Hệ thống không được dùng một phương pháp duy nhất cho mọi bộ ảnh.

## 3.1 Geometry Mode

Dùng khi ảnh có đủ overlap để khôi phục camera pose và scene.

Pipeline:

`Images -> Feature Matching -> SfM -> Camera Poses -> 3D Reconstruction/3DGS -> Camera Path -> Novel View Render`

Dùng cho:

- ngoại thất chụp nhiều góc
- nội thất chụp nhiều góc
- công trình có chuỗi ảnh liên tục
- walkthrough/flythrough

Đây là mode ưu tiên.

---

## 3.2 2.5D Mode

Dùng khi chỉ có một hoặc ít ảnh, hoặc reconstruction yếu.

Pipeline:

`Image -> Depth -> Segmentation/Layers -> 2.5D Point/Mesh Representation -> Small Camera Motion -> Warp/Render`

Chỉ cho phép chuyển động nhỏ:

- pan
- tilt
- small dolly
- small truck
- small crane
- parallax nhẹ

Không được giả tạo camera bay xa khỏi viewpoint gốc.

---

## 3.3 Transition Mode

Dùng khi hai ảnh không có quan hệ hình học đủ mạnh.

Ví dụ:

- exterior -> lobby
- living room -> bedroom
- daytime -> night
- ảnh chụp từ hai khu vực không overlap

Transition hỗ trợ:

- hard cut
- crossfade
- dip-to-black
- blur transition
- optional AI transition

Mặc định ưu tiên CUT/crossfade để bảo toàn kiến trúc.

AI transition là fallback, không phải pipeline chính.

---

# 4. Nguyên tắc cốt lõi

## 4.0. Luật bất biến

Các nguyên tắc dưới đây áp dụng cho mọi phase:

1. Không giả định mọi ảnh cùng một scene.
2. Geometry-first; generative video không phải engine mặc định.
3. Fidelity kiến trúc ưu tiên hơn camera "ấn tượng".
4. Camera chỉ được đi trong vùng dữ liệu hỗ trợ đủ tốt.
5. Geometry không đủ thì fallback, không hallucinate.
6. Rotation dùng quaternion/SLERP, không nội suy Euler trực tiếp.
7. Final render chỉ chạy sau path validation.
8. Original assets immutable.
9. GPU workload dài phải chạy qua worker/job abstraction.
10. Retry có giới hạn và lỗi phải observable.


## 4.1 Geometry-first

Luôn ưu tiên:

`Geometry -> Render -> AI Refine`

Không ưu tiên:

`Image A -> Generative Video Model -> Image B`

Lý do:

- generative video dễ đổi cửa
- đổi số lượng cột
- đổi texture
- biến dạng nội thất
- thay đổi tỉ lệ kiến trúc

---

## 4.2 Preserve architecture

Không được tùy ý tạo mới:

- cửa
- cửa sổ
- cột
- tường
- đồ nội thất chính
- facade detail
- kết cấu kiến trúc

AI refinement chỉ được:

- fill vùng thiếu nhỏ
- deartifact
- temporal cleanup
- anti-flicker
- sharpen
- upscale
- mild texture recovery

Nếu AI phải hallucinate vùng lớn, hệ thống phải giảm camera motion hoặc chuyển mode.

---

## 4.3 Camera motion phải bị giới hạn bởi dữ liệu

Không cho camera đi quá xa khỏi vùng đã được quan sát.

Mỗi frame phải có:

- visibility confidence
- reconstruction confidence
- novel-view distance score
- artifact risk score

Nếu quality score thấp hơn threshold:

1. giảm path amplitude
2. tăng số keyframe trung gian
3. đổi path
4. chuyển sang 2.5D
5. dùng cut/transition

---

# 5. Kiến trúc tổng thể

```text
                         INTERNET
                            |
                            v
                  +-------------------+
                  |   Web Frontend    |
                  | Next.js / React   |
                  +---------+---------+
                            |
                            v
                  +-------------------+
                  |   Backend API     |
                  |     FastAPI       |
                  +---------+---------+
                            |
        +-------------------+--------------------+
        |                   |                    |
        v                   v                    v
   PostgreSQL             Redis               S3/R2
   Metadata              Queue/State          Assets
        |                   |                    |
        +-------------------+--------------------+
                            |
                            v
                  +-------------------+
                  | Device Registry   |
                  | + Hybrid Router   |
                  +----+---------+----+
                       |         |
              Local    |         | Cloud
                       |         |
                       v         v
             +-------------+   +----------------+
             | Local Agent |   | Cloud GPU Pool |
             | User Device |   | GPU Workers    |
             +------+------+   +-------+--------+
                    |                  |
                    +--------+---------+
                             |
                             v
                  +----------------------+
                  | Cinematic Engine     |
                  | COLMAP / 3DGS / AI   |
                  | Camera / Render / FF |
                  +----------+-----------+
                             |
                             v
                           MP4
                             |
                             v
                           Storage
```

Hệ thống có **một Cinematic Engine dùng chung**, nhưng có nhiều execution targets.

Không tạo hai implementation khác nhau cho Local và Cloud.

```text
                    CINEMATIC ENGINE
                           |
                 +---------+---------+
                 |                   |
                 v                   v
          Local Worker         Cloud Worker
```

Khác biệt giữa Local và Cloud chỉ nằm ở:

- worker registration
- scheduling
- storage transfer
- billing
- lifecycle
- security boundary

---

# 5.1. Thành phần bắt buộc mới

## Device Registry

Quản lý các máy đã pair với user/team.

Phải biết:

- device_id
- owner_user_id / organization_id
- device_name
- OS
- CPU
- RAM
- GPU list
- VRAM
- CUDA/ROCm capability
- driver version
- runtime version
- agent version
- online/offline
- idle/busy
- last_seen
- current_job_id
- benchmark score
- supported job capabilities

## Local GPU Agent

Một chương trình cài một lần trên PC người dùng.

Nhiệm vụ:

- pair device
- authenticate với backend
- detect hardware
- detect CUDA/driver/runtime
- maintain outbound secure connection
- nhận job được phép
- tải asset cần thiết
- chạy Cinematic Engine
- stream progress
- upload result
- cleanup temporary data
- auto update có kiểm soát

Agent không được mở public inbound port.

Agent phải chủ động kết nối ra backend qua:

- HTTPS
- WSS
- hoặc gRPC over TLS nếu sau này cần

## Hybrid Job Router

Quyết định job chạy ở đâu.

Input:

- execution preference
- online devices
- GPU capability
- VRAM
- runtime compatibility
- job requirements
- user permission
- cloud price estimate
- queue time
- device busy state

Output:

- selected worker
- reason
- estimated cost
- estimated compatibility
- fallback plan

## Cloud GPU Pool

Cloud GPU Worker có cùng worker protocol với Local Agent.

Cloud worker phải:

- register capabilities
- heartbeat
- claim job
- download assets
- run engine
- upload artifacts
- release resources
- shutdown/scale down nếu idle

---

# 6. Tech stack mặc định

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Three.js hoặc React Three Fiber
- Zustand hoặc Redux Toolkit
- TanStack Query

## Backend

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery hoặc RQ

## Computer Vision / 3D

- OpenCV
- PyTorch
- COLMAP/PyCOLMAP
- gsplat hoặc Nerfstudio-compatible 3D Gaussian Splatting
- optional Open3D
- optional trimesh

## Video

- FFmpeg

## Storage

- S3-compatible storage
- MinIO cho local development

## Deployment

- Docker
- Docker Compose cho dev
- NVIDIA Container Toolkit cho Cloud GPU Worker
- production có thể dùng Kubernetes nhưng không bắt buộc ở MVP

## Local GPU Agent

MVP khuyến nghị:

- Python 3.11+
- packaged thành Windows app/service bằng PyInstaller hoặc Nuitka
- FastAPI/HTTP client nội bộ nếu cần
- WebSocket client hoặc long-lived HTTPS polling fallback
- subprocess orchestration cho COLMAP/FFmpeg/runtime
- managed virtual environment hoặc managed runtime bundle
- auto-start cùng Windows theo opt-in của user

Không bắt buộc user phải cài Docker.

Docker có thể là optional execution backend trên máy advanced user.

Về sau có thể chuyển shell/service layer sang Rust nếu cần:

- startup nhanh hơn
- binary gọn hơn
- update an toàn hơn
- giảm phụ thuộc Python ở lớp agent

Nhưng Cinematic Engine vẫn có thể giữ Python/PyTorch.

---

# 7. Repo structure

```text
image-to-video/
|
+-- apps/
|   +-- web/
|   +-- api/
|
+-- services/
|   +-- reconstruction/
|   +-- renderer/
|   +-- director/
|   +-- refinement/
|   +-- encoder/
|
+-- workers/
|   +-- cpu_worker/
|   +-- gpu_worker/
|
+-- packages/
|   +-- contracts/
|   +-- camera_math/
|   +-- path_planner/
|   +-- quality/
|   +-- shared/
|
+-- infra/
|   +-- docker/
|   +-- nginx/
|   +-- scripts/
|
+-- models/
|   +-- checkpoints/
|
+-- data/
|   +-- cache/
|   +-- temp/
|
+-- tests/
|   +-- unit/
|   +-- integration/
|   +-- golden/
|
+-- docs/
|
+-- docker-compose.yml
+-- Makefile
+-- README.md
+-- .env.example
+-- SKILL.md
```

---

# 8. Domain model

## Project

```python
class Project:
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
```

## ImageAsset

```python
class ImageAsset:
    id: UUID
    project_id: UUID
    uri: str

    width: int
    height: int

    exif: dict | None

    scene_id: UUID | None

    sharpness_score: float | None
    exposure_score: float | None
    feature_count: int | None

    created_at: datetime
```

## Scene

```python
class Scene:
    id: UUID
    project_id: UUID

    name: str

    mode: Literal[
        "geometry",
        "2.5d",
        "transition"
    ]

    reconstruction_status: str

    confidence: float

    representation_uri: str | None
```

## CameraKeyframe

```python
class CameraKeyframe:
    id: UUID
    scene_id: UUID
    image_id: UUID | None

    position: tuple[float, float, float]

    rotation_quaternion: tuple[
        float, float, float, float
    ]

    focal_length_mm: float
    sensor_width_mm: float

    timestamp_sec: float

    confidence: float

    locked: bool
```

## Shot

```python
class Shot:
    id: UUID
    project_id: UUID
    scene_id: UUID | None

    name: str

    duration_sec: float
    fps: int

    mode: str

    easing: str

    path_type: str
    tension: float

    camera_target: tuple[float, float, float] | None

    status: str
```

## RenderJob

```python
class RenderJob:
    id: UUID
    project_id: UUID
    shot_id: UUID | None

    type: Literal[
        "preview",
        "final",
        "full_movie"
    ]

    width: int
    height: int
    fps: int

    codec: str

    status: str
    progress: float

    output_uri: str | None

    error: str | None
```

## Device

```python
class Device:
    id: UUID
    owner_user_id: UUID
    organization_id: UUID | None

    name: str
    os: str
    agent_version: str

    cpu_name: str | None
    ram_gb: float | None

    status: Literal[
        "online",
        "offline",
        "busy",
        "degraded"
    ]

    last_seen_at: datetime
    current_job_id: UUID | None
```

## GPUDevice

```python
class GPUDevice:
    id: UUID
    device_id: UUID

    vendor: str
    model: str
    vram_gb: float

    cuda_available: bool
    cuda_version: str | None

    rocm_available: bool
    rocm_version: str | None

    driver_version: str | None

    benchmark_score: float | None

    capabilities: list[str]
```

## WorkerSession

```python
class WorkerSession:
    id: UUID

    worker_type: Literal[
        "local",
        "cloud"
    ]

    device_id: UUID | None

    status: str
    heartbeat_at: datetime

    active_job_id: UUID | None

    runtime_version: str
```

## ExecutionPlan

```python
class ExecutionPlan:
    job_id: UUID

    preference: Literal[
        "auto",
        "local",
        "cloud"
    ]

    selected_worker_type: Literal[
        "local",
        "cloud"
    ]

    selected_device_id: UUID | None

    required_vram_gb: float | None

    estimated_cloud_cost: float | None

    requires_cost_confirmation: bool

    routing_reason: str
```


---


# 8.1. Pairing Local GPU Agent

Lần đầu cài Agent:

1. Agent tạo temporary pairing session.
2. Backend cấp pairing code ngắn hạn.
3. User đăng nhập website.
4. User nhập code hoặc xác nhận device.
5. Backend bind device với user/team.
6. Agent nhận device credential riêng.
7. Pairing code hết hiệu lực.
8. Device credential được lưu an toàn trên máy.

Ví dụ UX:

```text
CineGPU Agent

Pairing code:
739 281
```

Website:

```text
Add computer
[ 739281 ]
```

Sau khi pair:

```text
Office-PC
RTX 4090 24GB
Online
```

Không dùng shared API key cho tất cả agent.

Mỗi device phải có credential riêng, rotate/revoke được.

---

# 8.2. Agent heartbeat

Agent gửi heartbeat định kỳ:

```json
{
  "device_id": "...",
  "status": "idle",
  "gpus": [
    {
      "name": "NVIDIA RTX 4090",
      "vram_gb": 24,
      "cuda": true
    }
  ],
  "runtime_version": "2.0.0"
}
```

Backend đánh dấu offline nếu heartbeat timeout.

Không được hiển thị device là Ready nếu heartbeat đã stale.

---

# 8.3. Worker capability negotiation

Mỗi job khai báo requirements.

Ví dụ:

```json
{
  "requires": {
    "cuda": true,
    "min_vram_gb": 12,
    "features": [
      "colmap",
      "3dgs",
      "ffmpeg"
    ]
  }
}
```

Router chỉ assign job cho worker đáp ứng đủ.

Không route theo tên GPU đơn thuần.

---

# 8.4. Local device discovery trong Web

Browser không tự scan GPU worker.

Flow đúng:

```text
Browser
  |
  v
Backend API
  |
  v
Device Registry
  |
  v
List paired devices
```

Frontend gọi:

```text
GET /api/v1/devices
```

và hiển thị:

```text
Office-PC
RTX 4090
Online
Ready
```

Nếu chính máy đang mở browser có Agent đã pair, frontend có thể hiển thị nhãn:

```text
This computer
```

nhưng nhãn này chỉ là UX.

Nguồn sự thật vẫn là Device Registry.

---

# 8.5. Agent security boundary

Agent tuyệt đối không hỗ trợ remote arbitrary command execution.

Không có API dạng:

```text
run_shell(command)
execute_python(code)
```

Agent chỉ nhận whitelist job types:

```text
ANALYZE_IMAGES
RECONSTRUCT_SCENE
TRAIN_3DGS
RENDER_SHOT
REFINE_VIDEO
ENCODE_VIDEO
FULL_PIPELINE
```

Mỗi job payload phải validate schema.

Agent phải:

- sandbox working directory theo job
- chỉ truy cập asset được cấp signed URL/token
- enforce timeout
- enforce disk quota
- enforce temp cleanup
- không đọc file ngoài workspace nếu không được user chọn
- không expose filesystem tùy ý
- không mở inbound port ra Internet

---

# 8.6. Local data strategy

Khi dùng My GPU, ưu tiên giảm upload/downloading không cần thiết.

Có hai mode:

## Cloud-backed assets

Ảnh đã upload lên storage.

Agent tải signed URLs về local cache.

Ưu điểm:

- cùng project dùng được từ nhiều máy
- đơn giản cho collaboration

## Direct local staging

Optional future feature.

Nếu user upload từ cùng máy có Agent:

- browser upload metadata
- Agent có thể nhận file bằng secure local handoff
- tránh upload/download vòng qua cloud cho asset lớn

Không bắt buộc cho MVP.

MVP dùng cloud-backed assets để giảm độ phức tạp.

---

# 8.7. Local vs Cloud result parity

Cùng một:

- engine version
- model version
- render settings
- camera path
- seed/config nếu applicable

thì Local và Cloud phải cho kết quả tương đương trong giới hạn sai số GPU/runtime.

Không duy trì hai code path render khác nhau.

---

# 8.8. Cloud cost confirmation

Cloud execution có thể phát sinh phí.

Trước khi assign paid cloud worker:

1. estimate GPU class
2. estimate runtime band
3. estimate cost band
4. hiển thị cho user
5. user xác nhận
6. tạo billing reservation/credit hold nếu hệ thống có billing
7. mới bắt đầu cloud job

Không tự thuê GPU chỉ vì Local Agent offline.

Auto mode cũng phải tuân thủ bước xác nhận chi phí.

---

# 8.9. Hybrid routing logic

Pseudocode:

```python
def route_job(job, user_preference, devices, cloud_offers):
    if user_preference == "local":
        device = choose_compatible_local_device(job, devices)

        if not device:
            raise NoCompatibleLocalDevice()

        return LocalExecution(device)

    if user_preference == "cloud":
        offer = choose_cloud_offer(job, cloud_offers)

        return CloudExecution(
            offer=offer,
            requires_confirmation=True
        )

    # AUTO

    local = choose_compatible_local_device(job, devices)

    if local:
        return LocalExecution(local)

    offer = choose_cloud_offer(job, cloud_offers)

    return CloudExecution(
        offer=offer,
        requires_confirmation=True
    )
```

Có thể mở rộng scoring:

```python
score = (
    capability_score
    + availability_score
    + expected_speed_score
    + locality_score
    - estimated_cost_penalty
    - queue_penalty
)
```

Nhưng không được override user choice rõ ràng.

---


# 9. Pipeline 1 — Image ingestion

Khi user upload:

1. Validate MIME.
2. Validate resolution.
3. Fix EXIF orientation.
4. Convert color profile nếu cần.
5. Generate thumbnail.
6. Extract EXIF.
7. Compute:
   - blur score
   - exposure score
   - contrast score
   - duplicate score
8. Detect near-duplicate images.
9. Store original immutable.
10. Store normalized working copy.

Không overwrite ảnh gốc.

---

# 10. Pipeline 2 — Scene grouping

Mục tiêu:

Phân ảnh thành các nhóm có quan hệ hình học.

Tính pairwise:

- local feature match count
- inlier ratio
- homography confidence
- fundamental/essential matrix confidence
- estimated relative pose confidence
- optional global embedding similarity

Xây graph:

- node = image
- edge = geometric relation
- weight = geometric confidence

Sau đó cluster graph.

Ví dụ:

```text
Scene A
img_01
img_02
img_03
img_04

Scene B
img_08
img_09

Unresolved
img_15
```

Không group chỉ dựa trên semantic similarity.

Hai ảnh cùng là “phòng khách” nhưng khác căn hộ không được coi là cùng scene.

---

# 11. Pipeline 3 — Camera reconstruction

Ưu tiên COLMAP/PyCOLMAP.

Các bước:

1. feature extraction
2. feature matching
3. geometric verification
4. incremental/global SfM
5. bundle adjustment
6. camera intrinsics estimation
7. camera pose export
8. sparse point cloud export

Output cho mỗi image:

```json
{
  "image_id": "...",
  "registered": true,
  "camera": {
    "position": [0.0, 1.6, 2.2],
    "quaternion": [0.0, 0.0, 0.0, 1.0],
    "fx": 1800.0,
    "fy": 1800.0,
    "cx": 960.0,
    "cy": 540.0
  },
  "confidence": 0.91
}
```

Nếu số ảnh registered thấp:

- thử alternate matcher
- thử resize images
- thử exhaustive matching cho scene nhỏ
- thử sequential matching cho chuỗi ảnh
- nếu vẫn thấp -> fallback mode

---

# 12. Pipeline 4 — 3D representation

Mode mặc định: 3D Gaussian Splatting.

Input:

- registered cameras
- sparse points
- source RGB images

Output:

- trained splat representation
- camera bounds
- visibility statistics
- optional depth maps
- optional occupancy proxy

Phải support:

- fast preview training
- final-quality training
- resume training
- checkpointing

Không bắt user chờ final reconstruction mới được chỉnh storyboard.

Workflow:

`fast reconstruction -> fast GS preview -> edit -> final GS -> final render`

---

# 13. 2.5D fallback

Nếu scene có ít ảnh hoặc không đủ overlap:

1. estimate depth
2. depth cleanup
3. foreground/background segmentation
4. create layered point cloud hoặc mesh
5. fill disocclusion conservatively
6. restrict virtual camera volume

Giới hạn camera displacement theo:

- median scene depth
- visible area
- depth confidence

Mặc định:

- chỉ cho phép displacement nhỏ
- không tự orbit lớn
- không tự quay sau vật thể

---

# 14. Camera system

Mỗi camera state:

```python
@dataclass
class CameraState:
    position: np.ndarray
    rotation: np.ndarray
    focal_length_mm: float
    sensor_width_mm: float
```

Không dùng Euler angle làm representation chính.

Rotation dùng quaternion.

---

# 15. Camera interpolation

## Position

Hỗ trợ:

- linear
- Catmull-Rom
- cubic Bezier
- B-spline

Default:

- 2 keyframe -> cubic/ease path nhỏ
- >= 3 keyframe -> Catmull-Rom centripetal

## Rotation

Dùng quaternion SLERP.

## Focal length

Interpolate độc lập.

Mặc định không zoom nếu user không yêu cầu.

---

# 16. Camera path controls

UI và API phải hỗ trợ:

- duration
- fps
- easing
- path type
- path tension
- speed
- smooth speed
- focal length
- camera roll
- look-at target
- path offset
- start handle
- end handle
- keyframe lock
- reverse shot

Easing presets:

- linear
- ease_in
- ease_out
- ease_in_out
- cinematic
- custom_bezier

---

# 17. Shot presets

Tối thiểu:

## Push In

Camera tiến về subject.

## Pull Out

Camera lùi khỏi subject.

## Truck Left/Right

Camera trượt ngang.

## Crane Up/Down

Camera nâng/hạ.

## Orbit

Camera quay quanh target.

## Reveal

Camera đi từ vùng che sang subject.

## Static + Parallax

Dùng cho 2.5D.

## Hero Hold

Chuyển động rất nhẹ quanh hero frame.

---

# 18. Camera target / look-at

Camera có thể:

- free rotation
- interpolate rotation
- look at fixed 3D point
- look at reconstructed feature cluster
- look at user-selected screen point

Khi look-at:

1. tính forward direction
2. preserve roll nếu không lock horizon
3. smooth target tracking
4. tránh abrupt rotation

---

# 19. Camera path quality

Mỗi path phải được chấm điểm.

```python
score = (
    w_smooth * smoothness_score
    + w_visibility * visibility_score
    + w_geometry * geometry_score
    + w_clearance * collision_clearance_score
    + w_reference * reference_similarity_score
)
```

Path bị reject nếu:

- đi ra ngoài camera bounds quá xa
- render uncertainty cao
- xuyên geometry proxy
- tạo quá nhiều newly exposed pixels
- rotation tốc độ quá lớn
- focal change quá lớn

---

# 20. Collision avoidance

Geometry proxy có thể đến từ:

- sparse point cloud
- depth fusion
- occupancy grid
- rough mesh
- scene bounds

Path planner cần:

1. sample path
2. query clearance
3. detect collision/risk
4. optimize control points
5. re-sample
6. validate

Không cần perfect physical collision ở MVP, nhưng phải tránh các lỗi rõ ràng.

---

# 21. Novel view validity

Mỗi virtual camera phải có:

```python
class ViewQuality:
    training_view_distance: float
    angular_difference: float
    visibility_coverage: float
    depth_confidence: float
    artifact_risk: float
    total_score: float
```

Nếu score thấp:

- path amplitude giảm
- camera target đổi
- shot ngắn lại
- insert source keyframe
- chuyển 2.5D
- chuyển cut

---

# 22. Renderer

Renderer phải nhận:

```python
render(
    scene_representation,
    camera_state,
    width,
    height
) -> Frame
```

Preview:

- 540p hoặc 720p
- reduced splat count
- fast settings

Final:

- 1080p/4K
- full representation
- antialiasing
- temporal-safe output

Mỗi frame lưu:

- RGB
- optional alpha
- optional depth
- camera metadata
- quality metadata

---

# 23. Temporal refinement

Không xử lý từng frame độc lập nếu có thể tránh.

Mục tiêu:

- giảm flicker
- giảm texture swimming
- ổn định edge
- xử lý small holes
- sharpen nhẹ
- upscale

Refinement phải có reference đến:

- previous frame
- next frame
- flow hoặc reprojection khi khả thi
- source views

Không dùng denoise quá mạnh làm mất texture kiến trúc.

---

# 24. AI inpainting rule

Chỉ inpaint khi:

- hole nhỏ
- vùng thiếu không phải structural feature lớn
- confidence đủ

Nếu hole lớn:

Không hallucinate toàn bộ.

Thay vào đó:

- reduce path movement
- switch camera
- cut
- use original image hold
- fall back to 2.5D

---

# 25. Storyboard

User có thể:

1. chọn ảnh
2. kéo thả thứ tự
3. group thành shot
4. chọn transition
5. chọn shot preset
6. chỉnh duration
7. preview

Storyboard model:

```text
Shot 01
Image 01 -> Image 02
Geometry
4.5 sec

Shot 02
Image 03
2.5D
3 sec

Shot 03
Scene A -> Scene B
Crossfade
1 sec
```

---

# 26. Automatic Director

Input:

- image groups
- quality scores
- scene types
- camera poses
- reconstruction
- target video duration

Output:

- shot sequence
- shot duration
- shot type
- keyframes
- transitions

Rules:

1. mở đầu bằng establishing shot nếu có
2. không dùng hai shot chuyển động giống nhau liên tiếp quá nhiều
3. tránh camera rotation gắt
4. không vượt vùng reconstruction an toàn
5. ưu tiên source images đẹp, sharp và có composition tốt
6. dùng cut giữa scenes không liên tục
7. giữ hero shot cuối
8. không tự hallucinate route giữa hai scene không liên quan

---

# 27. UI bắt buộc

## Project screen

- Create project
- Upload images
- Image grid
- Scene groups
- Processing state

## Scene screen

- source images
- reconstruction status
- camera map
- scene preview
- confidence

## Storyboard screen

- shot cards
- drag/drop
- transitions
- duration
- auto-direct button

## Camera editor

- 3D viewport
- camera path
- keyframe markers
- tangent handles
- target marker
- safe-view overlay
- artifact-risk overlay

## Timeline

- shots
- keyframes
- duration
- transition
- playhead
- preview

## Render screen

- render preset
- resolution
- FPS
- codec
- progress
- output

---

# 28. API contract

Prefix:

`/api/v1`

## Projects

```text
POST   /projects
GET    /projects
GET    /projects/{project_id}
DELETE /projects/{project_id}
```

## Assets

```text
POST   /projects/{project_id}/assets
GET    /projects/{project_id}/assets
DELETE /assets/{asset_id}
```

## Analyze

```text
POST /projects/{project_id}/analyze
GET  /projects/{project_id}/analysis
```

## Scenes

```text
GET  /projects/{project_id}/scenes
GET  /scenes/{scene_id}
POST /scenes/{scene_id}/reconstruct
GET  /scenes/{scene_id}/status
```

## Storyboard

```text
GET  /projects/{project_id}/storyboard
PUT  /projects/{project_id}/storyboard
POST /projects/{project_id}/auto-direct
```

## Shots

```text
POST   /projects/{project_id}/shots
GET    /shots/{shot_id}
PATCH  /shots/{shot_id}
DELETE /shots/{shot_id}
```

## Keyframes

```text
POST   /shots/{shot_id}/keyframes
PATCH  /keyframes/{keyframe_id}
DELETE /keyframes/{keyframe_id}
```

## Preview

```text
POST /shots/{shot_id}/preview
GET  /render-jobs/{job_id}
```

## Render

```text
POST /projects/{project_id}/render
GET  /render-jobs/{job_id}
POST /render-jobs/{job_id}/cancel
```

---


# 28.1. Device / Agent API

## Devices

```text
GET    /devices
GET    /devices/{device_id}
PATCH  /devices/{device_id}
DELETE /devices/{device_id}
POST   /devices/{device_id}/revoke
```

## Pairing

```text
POST /agent/pairing/start
POST /agent/pairing/confirm
POST /agent/pairing/exchange
```

## Agent session

```text
POST /agent/session/register
POST /agent/session/heartbeat
POST /agent/session/capabilities
POST /agent/session/job-events
POST /agent/session/job-complete
POST /agent/session/job-failed
```

## Execution planning

```text
POST /render-jobs/plan
POST /render-jobs/{job_id}/confirm-cloud-cost
POST /render-jobs/{job_id}/assign
```

Ví dụ plan response:

```json
{
  "mode": "auto",
  "recommended": {
    "type": "local",
    "device_id": "office-pc",
    "device_name": "Office PC",
    "gpu": "RTX 4090 24GB",
    "cloud_cost": 0
  },
  "alternatives": [
    {
      "type": "cloud",
      "gpu": "RTX 4090",
      "estimated_cost_vnd": 12000,
      "requires_confirmation": true
    }
  ]
}
```

---


# 29. Job state machine

```text
queued
  ->
preprocessing
  ->
matching
  ->
reconstructing
  ->
training_scene
  ->
ready
```

Render:

```text
created
  ->
planning
  ->
awaiting_execution_choice
  ->
awaiting_cost_confirmation   # chỉ khi cloud trả phí
  ->
queued
  ->
assigned
  ->
downloading_assets
  ->
processing
  ->
rendering
  ->
refining
  ->
encoding
  ->
uploading_result
  ->
completed
```

Local device disconnect:

```text
assigned/running
  ->
worker_lost
  ->
retry_wait
```

Sau đó:

- retry cùng device nếu quay lại
- route sang local device khác nếu user cho phép
- đề xuất Cloud GPU
- không tự chuyển sang paid Cloud nếu chưa được user xác nhận


Error:

```text
any_state -> failed
```

Cancel:

```text
queued/running -> cancel_requested -> cancelled
```

---

# 30. WebSocket / progress

Frontend phải nhận realtime progress.

Event:

```json
{
  "job_id": "...",
  "stage": "rendering",
  "progress": 0.62,
  "message": "Rendering frame 93/150"
}
```

Không dùng polling dày đặc nếu WebSocket/SSE khả thi.

---

# 31. Storage layout

```text
projects/{project_id}/
|
+-- originals/
+-- normalized/
+-- thumbnails/
+-- reconstruction/
|   +-- sparse/
|   +-- cameras/
|   +-- gs/
|
+-- scenes/
+-- previews/
+-- renders/
+-- exports/
```

Original file immutable.

---

# 32. Preview strategy

User không nên phải render final để xem camera.

Có 3 level:

## Level 1

Camera-only preview trong viewport.

Không render photoreal.

## Level 2

Low-res novel view preview.

## Level 3

Final quality render.

---

# 33. Video encoding

FFmpeg pipeline:

1. frame sequence
2. optional audio
3. transitions/compositing
4. encode

Default:

```text
H.264
yuv420p
1080p
30 fps
```

Final file cần:

- playable trên browser phổ biến
- metadata duration đúng
- no broken timestamp
- no missing frames

---

# 34. Audio

Optional.

Hỗ trợ:

- background music upload
- trim
- fade in/out
- volume
- mute
- sync shot cuts đơn giản theo beat nếu feature này được bật

Không để audio là dependency của video pipeline.

---

# 35. Error handling

Mỗi lỗi phải map sang user-facing action.

Ví dụ:

## Không đủ overlap

Hiển thị:

`Không đủ dữ liệu để dựng 3D ổn định. Hệ thống đã chuyển sang 2.5D.`

## Scene reconstruction lỗi

Cho phép:

- retry
- exclude bad images
- split scene
- use 2.5D

## GPU OOM

Tự:

- giảm resolution
- giảm batch
- release cache
- retry một lần
- nếu vẫn lỗi thì fail rõ ràng

Không loop retry vô hạn.

---

# 36. Quality gates

Một scene Geometry Mode chỉ được đánh dấu `ready` khi:

- registered image ratio đạt threshold
- reprojection error nằm trong ngưỡng
- đủ camera baseline
- scene representation train thành công
- sample novel views không lỗi nghiêm trọng

Một shot final chỉ được render nếu:

- path validated
- no critical collision
- mean view quality đạt threshold
- start/end frame hợp lệ

---

# 37. Unit tests bắt buộc

## Camera math

- quaternion normalize
- SLERP endpoints
- SLERP continuity
- look-at matrix
- focal conversion

## Path

- linear endpoints
- spline endpoints
- monotonic time
- easing
- duration mapping

## Quality

- invalid path rejection
- score bounds
- low-confidence fallback

## API

- create project
- upload
- create shot
- render request
- cancel job

## Device Registry

- pair device
- reject expired pairing code
- heartbeat
- offline timeout
- revoke device
- capability update

## Hybrid Router

- Auto chọn local compatible device
- Auto fallback cloud khi không có local
- không route job CUDA sang GPU incompatible
- Local mode fail rõ ràng nếu không có device phù hợp
- Cloud mode tạo cost confirmation
- Auto không tự phát sinh paid cloud cost
- busy device không nhận job mới nếu concurrency=1

## Local Agent

- chỉ nhận whitelist job type
- reject malformed payload
- download signed asset
- progress event
- cancel job
- worker disconnect/reconnect
- cleanup temp

---

# 38. Integration tests

Tạo fixture:

## Dataset A

Exterior, 20–30 ảnh, overlap tốt.

Expected:

- Geometry Mode
- camera reconstruction thành công
- orbit/push shot render được

## Dataset B

Interior, 10–20 ảnh.

Expected:

- Geometry Mode hoặc mixed fallback
- walkthrough nhỏ

## Dataset C

Một ảnh duy nhất.

Expected:

- 2.5D Mode
- camera displacement giới hạn

## Dataset D

Hai ảnh không liên quan.

Expected:

- Transition Mode
- không tạo fake 3D path

---


# 38.1. Evaluation datasets

Phải duy trì bộ dataset nội bộ có version. Ít nhất gồm:

| Dataset | Mục tiêu |
|---|---|
| Exterior Easy | nhiều ảnh, overlap tốt, ánh sáng ổn |
| Exterior Wide Baseline | góc nhìn thay đổi lớn |
| Interior Easy | phòng có texture/feature đủ |
| Interior Repetitive | tường phẳng, pattern lặp |
| Interior Reflective | kính/gương/bề mặt phản xạ |
| Low Light | noise/exposure khó |
| Wide Angle | distortion mạnh |
| Mixed Cameras | nhiều focal/device khác nhau |
| Sparse Images | ít ảnh, overlap yếu |
| Single Image | bắt buộc 2.5D |
| Disconnected Scenes | bắt buộc cut/transition |
| Bad Inputs | blur/duplicate/unsupported/low-res |

Mỗi dataset phải có:

```text
dataset_id
dataset_version
license/source
expected_mode
expected_registered_range
known_failure_modes
golden_shots
notes
```

Không dùng duy nhất một villa đẹp làm benchmark cho toàn sản phẩm.

---

# 38.2. Evaluation metrics

Không có một metric duy nhất đủ.

Theo dõi ít nhất:

## Reconstruction

- registered image ratio;
- reprojection/geometry error proxy;
- camera baseline coverage;
- failed image list.

## Camera path

- path smoothness;
- angular velocity;
- view-confidence distribution;
- collision/clearance risk;
- newly exposed/unobserved area proxy.

## Video

- temporal flicker proxy;
- frame artifact rate;
- start/end reference similarity;
- dropped/missing frames;
- encode validity.

## Product

- job success rate;
- median/percentile processing time;
- cost per job;
- retry rate;
- user-cancel rate.

Threshold pass/fail phải để config và calibrate bằng dataset thật.

---

# 38.3. Reproducibility và provenance

Mọi reconstruction/render final phải lưu provenance:

```json
{
  "engine_version": "x.y.z",
  "pipeline_schema_version": 1,
  "reconstruction_backend": "colmap",
  "reconstruction_backend_version": "...",
  "scene_backend": "3dgs",
  "scene_backend_version": "...",
  "model_versions": {},
  "checkpoint_hashes": {},
  "render_config_hash": "...",
  "camera_path_version": 1,
  "seed": 1234,
  "input_asset_hashes": []
}
```

Mục tiêu:

- debug được project cũ;
- render lại có thể giải thích vì sao khác;
- migrate project có kiểm soát;
- rollback khi engine version mới gây regression.

Không hứa exact pixel determinism giữa GPU/runtime khác nhau nếu backend không
đảm bảo; thay vào đó yêu cầu **semantic/config reproducibility** và golden
regression bounds.

---

# 39. Golden tests

Lưu các output chuẩn:

- camera path json
- keyframe json
- preview frames
- final frame samples

Dùng perceptual similarity để phát hiện regression.

Không yêu cầu exact pixel match cho GPU renderer.

---

# 40. Observability

Log:

- project_id
- job_id
- scene_id
- shot_id
- GPU
- stage
- timing
- memory usage
- failure reason

Metrics:

- reconstruction success rate
- registered image ratio
- median reconstruction time
- median preview time
- render fps
- failure by stage
- GPU utilization
- job queue latency

---

# 41. Security

- validate MIME bằng content, không chỉ extension
- sanitize filenames
- không execute file upload
- signed URLs
- project isolation
- organization isolation
- rate limits
- upload size limits
- temp file cleanup
- auth required trong production
- per-device credentials
- pairing code TTL
- credential revoke
- TLS bắt buộc
- Agent chỉ outbound connection
- không mở public inbound port trên máy user
- signed job payload hoặc authenticated job channel
- whitelist job types
- không arbitrary shell execution
- workspace isolation theo job
- local cache cleanup policy
- cloud worker ephemeral credential
- audit log cho device pairing, revoke, job assign và cloud billing confirmation

Local Agent là thành phần có quyền chạy native workload trên máy user nên phải được xem là security-critical.

---

# 42. Licensing / model policy

Trước khi ship commercial:

- kiểm tra license của tất cả CV/3D/model dependencies
- không bundle checkpoint có license không phù hợp
- lưu attribution nếu dependency yêu cầu
- tách optional model downloads khỏi core app nếu cần

---

# 43. Performance targets

MVP target:

- upload 20 ảnh không crash
- reconstruct scene tiêu chuẩn
- preview 720p
- render 1080p
- cancel job hoạt động
- resume reconstruction cơ bản

Production target:

- multiple GPU workers
- resumable jobs
- caching
- render retries
- signed export
- project autosave

---

# 44. Camera JSON format

```json
{
  "version": 1,
  "shot_id": "shot_001",
  "duration_sec": 5.0,
  "fps": 30,
  "path": {
    "type": "catmull_rom",
    "tension": 0.35,
    "easing": "cinematic"
  },
  "keyframes": [
    {
      "time": 0.0,
      "position": [0.0, 1.6, 2.2],
      "rotation": [0.0, 0.0, 0.0, 1.0],
      "focal_length_mm": 32.0
    },
    {
      "time": 5.0,
      "position": [1.2, 1.7, 1.4],
      "rotation": [0.0, 0.18, 0.0, 0.983],
      "focal_length_mm": 32.0
    }
  ]
}
```

---

# 45. Pseudocode camera render

```python
def render_shot(scene, shot):
    frames = int(shot.duration_sec * shot.fps)

    path = build_camera_path(
        shot.keyframes,
        path_type=shot.path_type,
        tension=shot.tension,
        easing=shot.easing,
    )

    validate_path(scene, path)

    for i in range(frames):
        t = i / max(frames - 1, 1)

        camera = sample_camera(path, t)

        quality = evaluate_view(scene, camera)

        if quality.total_score < MIN_RENDER_SCORE:
            camera = recover_camera(scene, path, camera, t)

        frame = render_scene(scene, camera)

        frame = temporal_refine(
            frame=frame,
            camera=camera,
            scene=scene,
        )

        save_frame(frame, i)
```

---

# 46. Pseudocode mode selection

```python
def select_mode(images, analysis):
    if len(images) == 1:
        return "2.5d"

    if analysis.geometry_confidence >= 0.75:
        return "geometry"

    if analysis.geometry_confidence >= 0.35:
        return "2.5d"

    return "transition"
```

Threshold phải config được.

---

# 47. Pseudocode fallback

```python
def build_shot(scene_a, scene_b=None):
    if scene_b and scene_a.id != scene_b.id:
        return make_transition_shot(
            type="crossfade"
        )

    if scene_a.mode == "geometry":
        path = plan_geometry_path(scene_a)

        if validate_path(scene_a, path):
            return path

    if scene_a.mode in ("geometry", "2.5d"):
        return plan_safe_2_5d_path(scene_a)

    return make_static_or_transition_shot()
```

---

# 48. Implementation roadmap chuẩn

## Phase 0 — Technical Spike

Chỉ làm:

- ingestion tối thiểu;
- COLMAP/SfM;
- một scene backend;
- camera path 2-3 keyframes;
- render 5 giây;
- FFmpeg encode;
- benchmark/log;
- fallback proof cho 2.5D/cut.

Không UI lớn; CLI hoặc UI tối giản chấp nhận được.

## Phase 1A — Core Project/App

- project;
- upload;
- normalized asset pipeline;
- database;
- storage;
- worker queue;
- basic frontend.

## Phase 1B — Reconstruction

- scene grouping;
- feature/matching;
- COLMAP;
- camera export;
- sparse preview;
- quality/failure state.

## Phase 1C — Scene Representation

- 3DGS train/save/resume;
- preview rendering;
- view-quality estimation.

## Phase 1D — Camera Editor

- keyframes;
- spline;
- quaternion SLERP;
- timing;
- easing;
- target/look-at;
- path validation.

## Phase 1E — Video

- render frames;
- preview;
- final render;
- FFmpeg;
- export;
- persistent RenderJob.

## Phase 1F — Fallback & Quality

- depth/2.5D;
- transition mode;
- collision proxy;
- view validity;
- temporal refinement cơ bản.

## Phase 2 — Hybrid GPU

- Device Registry;
- Local Agent;
- pairing/revoke;
- worker protocol;
- Hybrid Router;
- cloud worker pool;
- cloud cost confirmation;
- reconnect/retry.

## Phase 3 — Intelligence

- Auto Director;
- shot ranking;
- automatic path selection;
- quality-aware path optimization;
- advanced temporal refinement.

## Phase 4 — Commercial Scale

- billing/credits;
- team/org;
- autoscaling;
- quotas;
- analytics;
- SLO/SLA;
- backup/DR.

---

# 49. Definition of Done — Core MVP (Phase 1)

Core MVP chỉ được coi là hoàn thành khi user có thể:

1. mở web app hoặc local web build;
2. tạo project;
3. upload 10–30 ảnh;
4. hệ thống normalize/analyze;
5. phân scene hoặc báo input không đủ;
6. dựng ít nhất một Geometry scene trên dataset phù hợp;
7. fallback 2.5D với single-image;
8. dùng cut/transition với disconnected scenes;
9. xem camera positions;
10. chọn 2–4 ảnh làm keyframe;
11. tạo camera path;
12. preview path;
13. chỉnh duration/easing;
14. path validation chạy trước render;
15. render preview;
16. render final;
17. encode MP4;
18. tải/xem MP4;
19. cancel/retry job;
20. project và render metadata không mất sau restart;
21. failure reason/log đủ để debug;
22. provenance/version lưu cùng render.

Vertical slice bắt buộc:

```text
Upload
  -> Analyze
  -> Reconstruct/Fallback
  -> 2 Keyframes
  -> Safe Path
  -> Preview
  -> MP4
```

Hybrid GPU **không phải điều kiện để Core MVP hoàn thành**.

## Definition of Done — Hybrid GPU MVP (Phase 2)

Phase 2 chỉ được coi là hoàn thành khi:

1. user cài và pair Local GPU Agent;
2. website hiển thị device online/offline;
3. capability report phản ánh GPU/VRAM/runtime;
4. My GPU chỉ chọn compatible device;
5. Cloud GPU tạo execution plan và cost estimate;
6. paid cloud yêu cầu confirmation trước khi chạy;
7. Local và Cloud dùng cùng job/engine contract;
8. progress từ Local Agent xuất hiện trên web;
9. device disconnect chuyển job sang trạng thái recovery rõ ràng;
10. user có thể retry local, chọn local device khác hoặc xác nhận cloud;
11. revoke device có hiệu lực;
12. Agent không hỗ trợ arbitrary remote shell;
13. worker result upload/persist thành công.

---

# 50. Definition of Done — Production

Production-ready khi Core Engine và Hybrid GPU (nếu sản phẩm bật tính năng này) đã qua security/quality gate và có:

- auth
- organization/team support nếu cần
- project isolation
- signed storage
- Device Registry
- pairing/revoke flow
- Local Agent auto-start
- Local Agent auto-update strategy
- Local Agent version compatibility check
- Hybrid Job Router
- multiple local devices per user/team
- multiple cloud workers
- cloud scale-to-zero
- cloud cost confirmation
- render cancellation
- resumable job
- worker reconnect recovery
- autosave
- monitoring
- structured logs
- audit logs
- retries có giới hạn
- test coverage hợp lý
- GPU OOM recovery
- reconstruction fallback
- 2.5D fallback
- safe transition logic
- production deployment docs
- Agent install/uninstall docs
- backup strategy
- license audit
- security audit

---

# 51. UX nguyên tắc

Người dùng không cần biết:

- SfM
- Gaussian Splatting
- quaternion
- reprojection
- bundle adjustment

UI nên dùng ngôn ngữ:

- Analyze images
- Build scene
- Camera path
- Smoothness
- Movement
- Target
- Preview
- Render

Không expose thuật ngữ nghiên cứu trừ Advanced Settings.

---

# 52. Advanced Settings

Có thể mở:

- reconstruction matcher
- reconstruction quality
- GS training iterations
- path tension
- novel-view safety
- refinement strength
- output codec
- bitrate
- renderer quality

Mặc định phải tự động hợp lý.

---

# 53. Preset chất lượng

## Draft

- low-res reconstruction
- fast GS
- 540p
- no heavy refinement

## Preview

- medium reconstruction
- 720p
- lightweight refinement

## Final

- full scene
- 1080p/4K
- temporal refinement
- high quality encode

---

# 54. Các lỗi tuyệt đối phải tránh

Không:

1. nối mọi ảnh thành một path duy nhất
2. giả định mọi ảnh cùng scene
3. dùng Euler interpolation cho rotation
4. cho camera đi xa khỏi training views
5. hallucinate vùng kiến trúc lớn
6. dùng AI video generator làm engine mặc định
7. render final trước khi validate path
8. overwrite source image
9. chạy GPU job trực tiếp trong HTTP request
10. giữ file temp vô hạn
11. retry vô hạn
12. để một job OOM làm chết toàn worker pool

---

# 55. Coding rules cho agent

Khi triển khai feature:

1. xác định layer bị ảnh hưởng
2. cập nhật data contract trước
3. viết unit test cho camera/path math
4. viết API
5. viết worker logic
6. viết frontend
7. thêm error handling
8. thêm telemetry
9. chạy integration test
10. cập nhật docs

Không viết logic camera rải rác trong UI.

Camera math phải nằm trong package dùng chung.

---

# 56. Config

Ví dụ:

```yaml
app:
  env: development
  product_phase: 1
  pipeline_schema_version: 1

reconstruction:
  min_images_geometry: 3
  min_registered_ratio: 0.6
  geometry_confidence_threshold: 0.75

camera:
  max_angular_velocity_deg_sec: 45
  default_focal_mm: 32
  default_easing: cinematic
  default_path: catmull_rom

quality:
  min_render_score: 0.65
  max_artifact_risk: 0.35
  # calibration_required: true cho tới khi benchmark dataset đủ lớn
  calibration_required: true

render:
  preview_width: 1280
  preview_height: 720
  final_width: 1920
  final_height: 1080
  fps: 30
  codec: h264

storage:
  provider: s3
```

---

# 57. Environment variables

```text
DATABASE_URL=
REDIS_URL=

S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=

CUDA_VISIBLE_DEVICES=

FFMPEG_PATH=
COLMAP_PATH=

APP_BASE_URL=
JWT_SECRET=

DEVICE_PAIRING_SECRET=
AGENT_TOKEN_SIGNING_KEY=
AGENT_HEARTBEAT_TIMEOUT_SEC=

CLOUD_GPU_PROVIDER=
CLOUD_GPU_API_KEY=
CLOUD_GPU_MAX_HOURLY_COST=

REQUIRE_CLOUD_COST_CONFIRMATION=true
```

Không commit secret.

---

# 58. Local development

Mục tiêu:

```bash
docker compose up
```

phải khởi động:

- postgres
- redis
- minio
- api
- web
- cpu worker
- mock device registry
- optional mock cloud worker

Cloud GPU worker có thể chạy bằng profile riêng.

Ví dụ:

```bash
docker compose --profile gpu up gpu-worker
```

Local Agent chạy như một process riêng trên host để test pairing và device detection:

```bash
python -m agents.local_gpu_agent
```

Cho phép `DEV_AGENT_FAKE_GPU` để test routing trên laptop yếu mà không giả lập render production.

Ví dụ:

```text
DEV_AGENT_FAKE_GPU=NVIDIA_RTX_4090_24GB
```

Fake GPU chỉ dùng test routing/UI.

Không được dùng để bypass production capability check.


---

# 59. CLI nội bộ

Nên có CLI cho debug:

```bash
tool analyze ./dataset
tool reconstruct <scene_id>
tool train-gs <scene_id>
tool plan-shot <scene_id>
tool render-shot <shot_id>
tool encode <project_id>
```

CLI và API phải dùng chung service layer.

---

# 60. Acceptance scenario chính

Dataset:

- 24 ảnh exterior của một biệt thự
- chụp vòng quanh mặt tiền và sân

User flow:

1. upload 24 ảnh
2. hệ thống cluster thành 1 exterior scene
3. 21/24 ảnh registered
4. 3 ảnh bị đánh dấu low confidence
5. scene được reconstruct
6. 3DGS preview xuất hiện
7. user chọn image 03 làm start
8. image 10 làm mid
9. image 17 làm end
10. hệ thống tạo orbit/reveal path
11. path validation phát hiện gần facade
12. camera path tự offset
13. user preview
14. user chỉnh duration 7 sec
15. render 1080p 30fps
16. temporal refinement
17. encode H.264
18. output MP4

Kết quả phải:

- giữ hình học công trình
- camera mượt
- không xuyên facade
- không có flicker nghiêm trọng
- không đổi cửa/cột
- start/end gần giống source reference

---

# 61. Acceptance scenario fallback

Dataset:

- 1 ảnh phòng khách

Expected:

1. system chọn 2.5D
2. estimate depth
3. create layered scene
4. chỉ cho camera truck nhẹ
5. path range bị giới hạn
6. output 3–5 sec
7. không cố orbit 180 độ

---

# 62. Acceptance scenario unrelated images

Input:

- exterior.jpg
- lobby.jpg

Expected:

- không reconstruct chung
- không camera-fly xuyên tường
- tạo 2 shot
- nối bằng cut/crossfade
- optional AI transition chỉ khi user bật

---


# 62.1. Acceptance scenario — Office GPU

Setup:

- User mở website trên laptop bất kỳ.
- Office-PC đã cài Agent.
- Office-PC có RTX 4090.
- Office-PC đang online.

Expected:

1. `/devices` trả Office-PC online.
2. UI hiển thị:
   - Office-PC
   - RTX 4090 24GB
   - Ready
3. User chọn `My GPU`.
4. Router assign job cho Office-PC.
5. Office Agent download asset.
6. Agent chạy Cinematic Engine.
7. progress xuất hiện trên web.
8. MP4 upload về storage.
9. web hiển thị completed.
10. không phát sinh cloud GPU charge.

---

# 62.2. Acceptance scenario — Laptop yếu

Setup:

- User mở website trên laptop AMD Radeon 520.
- Không có compatible Local device khác online.

Expected:

1. Radeon 520 bị đánh dấu incompatible cho Geometry 3DGS CUDA pipeline.
2. `My GPU` disabled hoặc hiển thị rõ unsupported.
3. `Cloud GPU` available.
4. UI hiển thị estimated cloud cost.
5. Không chạy cloud trước khi user xác nhận.
6. Sau confirm, cloud worker nhận job.
7. kết quả trả về web bình thường.

---

# 62.3. Acceptance scenario — Dùng PC công ty từ nhà

Setup:

- User ở nhà mở website.
- Home laptop yếu.
- Office-PC RTX 4090 vẫn bật Agent.

Expected:

1. Website thấy cả hai device qua Device Registry.
2. User chọn Office-PC.
3. Browser không cần kết nối trực tiếp LAN với Office-PC.
4. Office Agent nhận job qua outbound secure connection.
5. render chạy tại công ty.
6. result xuất hiện trong cùng project ở nhà.

---

# 62.4. Acceptance scenario — Local worker mất mạng

Setup:

- Local RTX 4090 đang render.
- Mạng Office-PC mất giữa job.

Expected:

1. heartbeat timeout.
2. job chuyển `worker_lost`.
3. project không mất.
4. partial checkpoint được giữ nếu engine hỗ trợ.
5. UI hiển thị lựa chọn:
   - Retry Office-PC
   - Another Local Device
   - Use Cloud GPU
6. nếu chọn Cloud -> phải xác nhận cost trước.
7. không tự phát sinh charge.

---

# 62.5. Acceptance scenario — Nhiều máy trong studio

Setup:

```text
PC-01 RTX4090 idle
PC-02 RTX4090 busy
PC-03 RTX3090 idle
```

Auto mode expected:

- Router loại PC-02 nếu concurrency đầy.
- Chọn PC-01 hoặc PC-03 theo capability/speed.
- Không chọn Cloud nếu compatible local worker đang rảnh, trừ khi policy/user preference nói khác.

---


# 63. Future extensions

Sau core product có thể thêm:

- BIM/CAD import
- GLB/FBX/USD import
- floor plan guidance
- user-drawn camera route
- object tracking
- relighting
- day-to-night
- people/vehicle animation
- depth-aware text/logo
- automatic music edit
- multi-camera templates
- collaborative projects
- cloud GPU autoscaling

---

# 64. Nguyên tắc quyết định cuối cùng

Khi có xung đột giữa:

- camera đẹp
- fidelity kiến trúc

luôn ưu tiên:

`fidelity kiến trúc`

Khi có xung đột giữa:

- camera di chuyển lớn
- novel-view confidence

luôn ưu tiên:

`novel-view confidence`

Khi geometry không đủ:

`fallback`

không:

`hallucinate`

---

# 65. Mệnh lệnh cho coding agent

Khi được yêu cầu build hoặc sửa sản phẩm:

1. đọc front matter, section 0, luật bất biến và phase hiện tại;
2. xác định task thuộc Phase 0/1/2/3/4;
3. không kéo dependency của phase sau vào phase hiện tại nếu không cần;
4. kiểm tra repo hiện tại và giữ phần chạy tốt;
5. không rewrite toàn bộ chỉ để "đúng style";
6. cập nhật contract/schema trước khi code cross-service;
7. camera/path math phải có unit test;
8. mọi job dài phải qua worker abstraction;
9. original asset immutable;
10. mọi threshold phải config;
11. mọi failure phải có reason + telemetry;
12. không mock reconstruction trong production path;
13. fake GPU chỉ dùng dev/test routing;
14. optional model thiếu thì degrade gracefully;
15. camera path phải validate trước final render;
16. AI refinement không được tự do thay đổi kiến trúc;
17. paid cloud không chạy nếu chưa xác nhận;
18. Agent không chạy arbitrary remote command;
19. Local/Cloud dùng chung engine/job contract;
20. thay đổi architecture/API/state machine phải cập nhật SKILL.md này;
21. benchmark trước khi tối ưu cost/GPU;
22. nếu task vượt phase gate hiện tại, báo rõ dependency/gate thay vì âm thầm build tắt.

Khi "build cả sản phẩm", thứ tự mặc định là:

```text
Phase 0 technical spike
  -> Phase 1 Core Engine
  -> quality gate
  -> Phase 2 Hybrid GPU
  -> Phase 3 Intelligence
  -> Phase 4 Commercial Scale
```

Không đảo thứ tự chỉ để demo UI lớn trước khi engine được chứng minh.

---

# 66. North-star workflow

Sản phẩm hoàn chỉnh cuối cùng phải cho cảm giác:

```text
UPLOAD
  ↓
ANALYZE
  ↓
BUILD SCENE / FALLBACK
  ↓
STORYBOARD
  ↓
EDIT CAMERA
  ↓
PREVIEW
  ↓
[PHASE 2+] CHOOSE EXECUTION
  ├── MY GPU
  ├── CLOUD GPU
  └── AUTO
  ↓
VALIDATE
  ↓
RENDER
  ↓
EXPORT
```

Người dùng cần ít thao tác nhất có thể, nhưng vẫn có quyền kiểm soát camera giống một công cụ 3D chuyên nghiệp.

---

# 67. Tóm tắt kiến trúc cốt lõi

```text
Images
  ↓
Image QA
  ↓
Scene Grouping
  ↓
Camera Pose / SfM
  ↓
3DGS or 2.5D
  ↓
Camera Keyframes
  ↓
Spline + SLERP + Easing
  ↓
Validity + Collision Check
  ↓
Novel View Renderer
  ↓
Temporal Refinement
  ↓
FFmpeg
  ↓
Final Video
```

Đây là pipeline chuẩn của sản phẩm.

Không được rút gọn thành:

```text
Images -> AI video -> MP4
```

nếu mục tiêu là giữ tính chính xác của dự án kiến trúc.

---

# 68. Kiến trúc Hybrid GPU — Quy tắc cuối cùng

Từ Phase 2 trở đi, sản phẩm phải xem GPU là **execution resource có thể thay đổi**, không phải một phần cố định của web server.

Model đúng:

```text
Project
  |
Render Job
  |
Execution Plan
  |
  +-- Local Device
  |      |
  |      +-- Local GPU Agent
  |
  +-- Cloud Device
         |
         +-- Cloud GPU Worker
```

Project, storyboard và camera path không phụ thuộc nơi render.

Một project có thể:

- preview bằng Office RTX4090
- final render bằng Cloud RTX4090
- render lại shot khác bằng Home RTX3090

mà không đổi project format.

---

# 69. Nguyên tắc ưu tiên execution

Nếu user chọn rõ:

```text
My GPU
```

thì không tự đổi sang Cloud.

Nếu user chọn:

```text
Cloud GPU
```

thì không tự gửi job sang Local.

Nếu user chọn:

```text
Auto
```

thì ưu tiên:

1. compatible local device online và idle
2. compatible local device online nhưng queue ngắn
3. cloud offer phù hợp

Nếu bước 3 tốn tiền:

- hiển thị cost
- yêu cầu confirm

---

# 70. Không được làm

Không:

- để browser tự tải arbitrary native executable khi user bấm render
- tự chạy shell command trên PC user từ server
- scan LAN của user từ web app
- mở port router tự động
- yêu cầu disable firewall
- dùng một shared agent token cho tất cả máy
- route job của User A sang GPU User B nếu chưa xây marketplace/permission layer
- tự thuê cloud GPU có phí mà không có xác nhận
- phụ thuộc PC developer
- duy trì hai render engine khác nhau cho Local và Cloud

---

# 71. North-star architecture

```text
                   WEB SaaS
                      |
                      v
                  Backend
                      |
             Device Registry
                      |
                 Job Router
              /             \
             /               \
            v                 v
      My GPU Agent       Cloud GPU
            \                 /
             \               /
              +-------------+
                    |
            Cinematic Engine
                    |
                   MP4
```

Đây là kiến trúc execution đích từ Phase 2 trở đi; Core Engine Phase 0-1 không phụ thuộc Hybrid GPU.

---

# 72. Canonical invariants — checklist cuối cùng

Trước khi merge một thay đổi lớn, kiểm tra:

## Fidelity

- Có thể làm thay đổi cửa/cột/tường/facade không?
- Nếu có, thay đổi đó có bị chặn hoặc fallback không?

## Camera

- Rotation có dùng quaternion/SLERP?
- Path có nằm trong vùng view confidence đủ?
- Có validate collision/visibility trước final render?

## Data

- Original asset có immutable?
- Project/render có provenance/version?
- Job restart có làm mất state không?

## Worker

- Workload dài có chạy ngoài HTTP request?
- OOM/crash có cô lập được?
- Retry có giới hạn?

## Phase

- Feature này thuộc phase nào?
- Phase gate trước đó đã pass chưa?
- Có đang vô tình kéo Hybrid GPU vào Core spike không?

## Hybrid GPU

- User có quyền với device?
- Capability có đủ?
- Agent chỉ outbound và chỉ chạy whitelist job?
- Paid cloud đã được xác nhận?

## Operability

- Có log/metric?
- Có test?
- Có acceptance path?
- Threshold mới có ở config?
- Có benchmark trước/sau?

Nếu một câu trả lời quan trọng là "không", chưa coi feature là hoàn chỉnh.

---

# 73. Tuyên bố nguồn chuẩn

File này là specification chuẩn duy nhất của project Image-to-Cinematic-Video.

Mục tiêu dài hạn:

```text
Images
  -> trustworthy scene understanding
  -> camera-consistent reconstruction/fallback
  -> quality-aware camera planning
  -> deterministic-enough rendering workflow
  -> optional Hybrid GPU execution
  -> stable final video
```

Sản phẩm không được đánh đổi độ trung thực kiến trúc để lấy chuyển động camera
ấn tượng nhưng không được dữ liệu hỗ trợ.

Khi geometry không đủ:

```text
FALLBACK
```

không:

```text
HALLUCINATE
```

