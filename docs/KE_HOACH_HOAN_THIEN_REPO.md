# Kế hoạch triển khai hoàn thiện repository AI-Video-

> **Mục tiêu:** biến `AI-Video-` từ prototype tạo video từ ảnh thành ứng dụng web có pipeline hình học 3D đáng tin cậy, dựng camera path, xuất MP4 ổn định, chạy được trên GPU local; sau khi lõi đã được kiểm chứng mới mở rộng sang lưu trữ cloud và worker GPU từ xa.
>
> **Repository:** [hieudang99dd/AI-Video-](https://github.com/hieudang99dd/AI-Video-)  
> **Ngày lập kế hoạch:** 2026-10-12  
> **Phạm vi tài liệu:** kế hoạch kỹ thuật, thứ tự thực hiện, tiêu chí nghiệm thu và hướng dẫn cho coding agent. Đây không phải xác nhận rằng các bước bên dưới đã được triển khai hoặc benchmark thành công.

---

## 0. Cách sử dụng tài liệu này

1. Đọc toàn bộ tài liệu trước khi sửa code.
2. Xác minh lại trạng thái của branch đang làm việc; không giả định mọi nhận xét trong tài liệu vẫn đúng nếu code đã thay đổi.
3. Thực hiện **từng phase theo thứ tự**. Mỗi phase phải có test và tiêu chí nghiệm thu riêng.
4. Ưu tiên sửa hoặc mở rộng code hiện có. Không tạo pipeline, schema, worker hoặc renderer thứ hai chỉ vì tiện.
5. Không đánh dấu task hoàn thành chỉ vì code đã viết hoặc API trả HTTP 200. Phải có bằng chứng từ test, log, artifact và/hoặc benchmark.
6. Mỗi thay đổi nên nhỏ, có thể review, có test hồi quy và một commit dễ hiểu.
7. Nếu thiếu GPU, dữ liệu benchmark hoặc dependency, ghi rõ điều kiện chưa kiểm chứng. Không giả lập kết quả geometry.

### Trạng thái quy ước

- `TODO`: chưa triển khai hoặc chưa có bằng chứng đủ để xác nhận.
- `IN PROGRESS`: đang triển khai.
- `BLOCKED`: đang chờ dependency, dữ liệu, quyền truy cập hoặc quyết định.
- `DONE`: code đã merge, test liên quan đã chạy và tiêu chí nghiệm thu đã đạt.
- `VERIFIED ON GPU`: chỉ dùng khi pipeline đã chạy thật trên máy có GPU được ghi lại trong benchmark.

---

## 1. Tầm nhìn sản phẩm và định nghĩa hoàn thành

AI-Video- hướng tới công cụ tạo video cinematic cho ảnh công trình, hạ tầng giao thông và dự án kỹ thuật (ví dụ ảnh xuất từ Civil 3D / InfraWorks). Người dùng cần có thể tải ảnh, tổ chức cảnh, chọn chuyển động camera, xem trước, render và xuất MP4 mà không bị nhầm giữa chuyển động 2D và tái dựng 3D.

### 1.1. Luồng sản phẩm mục tiêu

```text
Tạo Project
  -> Upload ảnh và xác thực file
  -> Phân tích chất lượng ảnh
  -> Chia ảnh thành Scene có bằng chứng hình học
  -> Chọn chế độ: Geometry / 2.5D / chuyển cảnh
  -> COLMAP tái dựng camera + sparse point cloud
  -> Kiểm tra chất lượng và lưu diagnostics
  -> Huấn luyện 3DGS bằng Nerfstudio/Splatfacto
  -> Xem scene và biên tập Camera Path / Keyframes
  -> Validate camera path
  -> Render frame sequence
  -> FFmpeg encode MP4
  -> FFprobe + QC + lưu artifact
  -> Tải video và xem provenance
```

### 1.2. Definition of Done cấp sản phẩm

Chỉ coi lõi sản phẩm hoàn thành khi tất cả điều kiện sau đúng:

- [ ] Luồng upload → project/scene → reconstruction → camera path → render → MP4 hoạt động end-to-end trên bộ dữ liệu benchmark.
- [ ] Hệ thống phát hiện rõ thiếu COLMAP, thiếu `ns-train`, thiếu `ns-render`, CUDA/VRAM không đủ, ảnh thiếu overlap và output lỗi.
- [ ] Không báo Geometry Mode thành công nếu thực tế chỉ tạo chuyển động crop/pan/zoom trên ảnh 2D.
- [ ] Một job có trạng thái, tiến độ, log, lỗi có thể đọc, yêu cầu hủy và kết quả đầu ra nhất quán.
- [ ] Có kiểm tra MP4 bằng FFprobe; file tồn tại hoặc kích thước lớn không được xem là đủ để chứng minh video hợp lệ.
- [ ] Camera path dùng một schema chuẩn; frontend, API, validator và renderer không tự tạo format cạnh tranh.
- [ ] Có unit test, API/integration test, test fallback và benchmark geometry.
- [ ] Có Docker build reproducible cho CPU/web/API và image GPU được kiểm chứng riêng.
- [ ] License, dependency versions, cấu hình và provenance được ghi nhận.
- [ ] Tài liệu hướng dẫn cài đặt, chạy, kiểm thử, khắc phục lỗi và backup được cập nhật.

**Không phải Definition of Done giai đoạn đầu:** GPU marketplace, thanh toán GPU thuê, multi-tenant SaaS hoàn chỉnh, realtime collaboration, hoặc tích hợp nhiều engine 3DGS. Các mục này chỉ bắt đầu sau khi geometry pipeline vượt benchmark.

---

## 2. Kiến trúc đích và nguyên tắc bất biến

### 2.1. Các thành phần

| Thành phần | Công nghệ / vị trí | Trách nhiệm |
|---|---|---|
| Web app | `apps/web` — Next.js | Project, upload, scene browser, camera path editor, job progress, preview và download |
| API | `apps/api/app` — FastAPI | Validation, quyền truy cập, CRUD, tạo job, capability endpoint |
| Database | PostgreSQL (SQLite cho dev nếu hỗ trợ) | Project, assets, scenes, shots, jobs, metadata |
| Queue | Redis khi có; cơ chế DB polling là fallback dev | Đưa job tới worker; không chạy render lâu trong HTTP request |
| CPU worker | `apps/api/app/workers/render_worker.py` | QA ảnh, fallback 2.5D, assembly timeline, encode/QC |
| GPU worker | Cùng hợp đồng job, image/runtime GPU riêng | COLMAP + Nerfstudio training/rendering và các bước cần CUDA |
| Geometry adapter | `apps/api/app/services/geometry_backend.py` | Interface ổn định, capability gate, orchestration engine |
| Geometry packages | `packages/colmap`, `packages/geometry` | Parser COLMAP, coordinate conversion, camera path, keyframe selection |
| Scene grouping | `packages/scene_grouping` | Gom ảnh theo bằng chứng liên kết hình học |
| Path validation | `packages/path_validation` | Kiểm tra camera path và đưa ra lý do chấp nhận/từ chối |
| Renderer | `apps/api/app/services/renderer.py` | Render fallback, gọi geometry render, encode, QC |
| Storage adapter | `apps/api/app/services/storage.py` | Đường dẫn logic và thao tác file; cho phép chuyển từ local sang object storage |
| Observability | log, job provenance, health/capability endpoints | Theo dõi lỗi, phiên bản, tài nguyên và thời gian |

### 2.2. Nguyên tắc không được phá vỡ

1. **Không xử lý render nặng trong API request.** API chỉ validate và tạo job.
2. **Không giả lập geometry.** Nếu geometry không khả dụng hoặc không đạt quality gate, trả lỗi có hướng dẫn hoặc dùng fallback đúng nhãn.
3. **Một camera-path schema duy nhất.** Schema canonical hiện ở `packages/geometry/camera_path.py`; mọi UI/engine phải chuyển đổi qua adapter.
4. **Một job lifecycle dùng chung.** Không thêm một hệ thống queue khác cạnh `RenderJob` và `queue.py` nếu chưa có ADR giải thích.
5. **Không phụ thuộc đường dẫn máy cá nhân.** Mọi file được định vị thông qua storage adapter và workspace theo project/scene/job.
6. **Tác vụ ngoài process phải có timeout, log, exit-code handling và cancellation strategy.**
7. **Artifact lớn không commit vào Git.** Ảnh, database COLMAP, point cloud, checkpoint, frames và MP4 nằm trong storage.
8. **Chất lượng có bằng chứng.** Lưu input manifest, engine/config version, metrics, rejection reasons và QC report.
9. **Không sao chép nguyên repo ngoài.** Chỉ học thuật toán, pattern hoặc tích hợp qua adapter; kiểm tra license trước khi copy code/model.
10. **Geometry và độ chính xác kỹ thuật được ưu tiên hơn hiệu ứng đẹp nhưng sai hình học.** AI video generative nếu bổ sung sau này phải là mode riêng, không tự thay đổi hình học công trình trong mode kỹ thuật.

---

## 3. Đánh giá điểm xuất phát và các rủi ro cần xử lý

Những nhận xét dưới đây dựa trên review code tĩnh của một snapshot repository. Trước khi sửa, agent phải xác minh lại trên branch mới nhất và chạy test để xác nhận.

| Mức độ | Khu vực | Rủi ro / việc cần xác minh | Hướng xử lý |
|---|---|---|---|
| P0 | Docker CPU | `apps/api/Dockerfile` copy `apps/api/app` nhưng không copy root `packages/`, trong khi code import `packages.*` | Thiết kế package/build context thống nhất; test import bên trong image |
| P0 | Docker GPU | `Dockerfile.gpu` có nhiều `FROM`, cài Nerfstudio lặp, copy `scripts` root có thể không tồn tại, và nhiều `CMD` | Chỉ giữ một base image có chủ đích; kiểm tra đường dẫn copy; tách image API/worker nếu cần |
| P0 | Geometry gate | Capability hiện cần kiểm tra riêng COLMAP, `ns-train`, `ns-render`, CUDA; training và rendering là hai khả năng khác nhau | Chuẩn hóa capability contract và reason codes |
| P0 | Command runner | subprocess trong geometry/render cần timeout, log đủ dùng, cancellation và tránh treo worker | Xây helper chạy process dùng chung hoặc module riêng, có test |
| P0 | Output QC | `qc_video_output` hiện kiểm tra file/kích thước cơ bản | Dùng FFprobe để xác nhận codec/container, resolution, FPS, duration, stream và decode khi cần |
| P0 | Geometry E2E | Có adapter chưa chứng minh pipeline đã chạy trên GPU thật | Chạy benchmark exterior/interior, lưu output và metrics |
| P1 | Camera path API | `Shot` có JSON `keyframes`, nhưng contract API chưa cung cấp CRUD/validation đầy đủ cho camera path | Thêm schema/versioning, GET/PUT, validation và round-trip tests |
| P1 | Scene grouping | Thuật toán grouping cần được nối với evidence từ ảnh/COLMAP, không chỉ tồn tại như package độc lập | Đưa vào scene creation/analysis workflow và lưu lý do gom/tách |
| P1 | Frontend | UI hiện có project/upload/storyboard/render job; cần scene status và editor keyframe/timeline thực sự | Phát triển từng lát dọc, không làm UI giả chỉ để trông hoàn chỉnh |
| P1 | Job robustness | DB polling và Redis path cần tránh chạy trùng job, job bị kẹt, hoặc progress lùi | Quy định atomic claim/lease, heartbeat, retry policy, cancel semantics |
| P1 | Storage | Cấu hình hiện hướng local; chưa phải kiến trúc cloud đa người dùng | Chuẩn hóa URI, storage adapter, cleanup/quota trước khi thêm S3-compatible storage |
| P1 | Security | Upload và đường dẫn file cần chống file giả, path traversal, quá tải tài nguyên | Giới hạn file, validate MIME/content, tên nội bộ ngẫu nhiên, quyền truy cập theo project |
| P2 | SaaS/cloud GPU | Chưa có worker registry, auth, remote job dispatch hay object storage production | Chỉ bắt đầu sau các gate geometry và security |
| P2 | Nhiều engine | Tích hợp đồng thời nhiều engine tăng bề mặt lỗi và khó benchmark | Giữ Nerfstudio/Splatfacto là đường chính; engine khác chỉ làm spike có số liệu |

---

## 4. Phase 0 — Khóa baseline, môi trường và khả năng tái lập

**Mục tiêu:** mọi developer/agent biết code nào là nguồn chuẩn, cách chạy test, và trạng thái nào đã được xác minh.

### Công việc

- [ ] Kiểm tra branch, commit SHA, working tree và file thay đổi trước khi làm.
- [ ] Đọc `README.md`, `SKILL_CANONICAL.md`, `docs/PHASE0_CHECKLIST.md`, `docs/BENCHMARK_DATASETS.md`, `docs/DEPENDENCY_LICENSE_GATE.md`, `docs/EXTERNAL_REPO_SOURCE_MAP.md` và tài liệu tích hợp repo hiện có.
- [ ] Lập bảng inventory cho Python, Node, CUDA, PyTorch, COLMAP, Nerfstudio, gsplat, FFmpeg, PostgreSQL và Redis.
- [ ] Ghi lệnh test hiện có, test pass/fail, Docker build pass/fail; không sửa test để né lỗi.
- [ ] Thêm hoặc cập nhật `docs/PROJECT_STATUS.md` nếu chưa tồn tại: trạng thái từng phase, commit đã kiểm tra, môi trường, lệnh test, blocker và ngày kiểm chứng.
- [ ] Pin phiên bản dependency quan trọng sau khi đã chọn và kiểm thử; tránh pin tùy tiện trước benchmark.
- [ ] Kiểm tra `.env.example` không chứa secret thật.

### Nghiệm thu

- Có baseline report gồm commit SHA, môi trường, test đã chạy, lỗi đã biết.
- Người khác có thể chạy hướng dẫn quick start từ repo sạch.
- Không có claim Geometry Mode verified nếu chưa có bằng chứng GPU.

---

## 5. Phase 1 — Sửa packaging và Docker trước khi phát triển tính năng

**Ưu tiên P0.** Mục tiêu là API/worker import được package nội bộ ổn định trong local và container.

### 5.1. Python package layout

- [ ] Xác định cách đóng gói canonical cho `packages/colmap`, `packages/geometry`, `packages/camera_math`, `packages/scene_grouping`, `packages/path_validation`.
- [ ] Chọn một chiến lược nhất quán:
  - cài đặt editable/package workspace từ root; hoặc
  - cấu hình build để package nội bộ được cài vào image; hoặc
  - dùng source tree rõ ràng và bảo đảm `PYTHONPATH` được thiết lập ở mọi entry point.
- [ ] Không giải quyết lỗi import bằng cách thêm nhiều đường dẫn tương đối phụ thuộc thư mục chạy.
- [ ] Kiểm tra các lệnh sau trong môi trường sạch:
  - import `app.main`;
  - import `app.services.geometry_backend`;
  - import `packages.geometry.camera_path`;
  - chạy worker bằng module entry point.

### 5.2. Docker CPU/API/worker

- [ ] Sửa `apps/api/Dockerfile` để mọi package được copy/cài đặt đúng.
- [ ] API và worker nên dùng cùng base application image khi dependency giống nhau; command có thể khác nhau.
- [ ] Giữ FFmpeg path cấu hình được.
- [ ] Không cài COLMAP/engine nặng vào CPU image nếu image đó không dùng chúng hoặc việc cài làm image khó tái lập; quyết định phải được ghi rõ.
- [ ] Kiểm tra healthcheck và thứ tự khởi động database/Redis.
- [ ] Đảm bảo worker chạy bằng command được khai báo trong Compose, không phụ thuộc terminal local.

### 5.3. Docker GPU

- [ ] Làm sạch `apps/api/Dockerfile.gpu`: một base image, một lần cài engine, các lệnh COPY hợp lệ, một command mặc định rõ ràng.
- [ ] Xác nhận CUDA/PyTorch/gsplat/Nerfstudio tương thích với nhau trên GPU mục tiêu.
- [ ] Đưa `check_gpu_env.py` vào đúng vị trí; test script thực sự có trong image.
- [ ] Không coi `docker build` thành công là bằng chứng GPU hoạt động; chạy container với GPU được expose và kiểm tra CUDA.
- [ ] Xem xét tách image CPU worker và GPU worker để web/API không phải mang toàn bộ dependency CUDA.
- [ ] Thêm profile/service GPU riêng trong Compose hoặc tài liệu chạy GPU; không làm mọi máy dev phải có GPU.

### Nghiệm thu

- [ ] Docker build CPU thành công.
- [ ] API và worker khởi động được từ image vừa build.
- [ ] Import packages nội bộ pass trong container.
- [ ] GPU image build và capability check pass trên máy có GPU tương thích.
- [ ] Có lệnh build/run chính xác được ghi vào README.

---

## 6. Phase 2 — Capability contract và process runner

**Mục tiêu:** hệ thống biết chính xác bước nào chạy được và không treo vô hạn khi engine lỗi.

### 6.1. Chuẩn hóa capability

Sửa `apps/api/app/services/capabilities.py` và mọi consumer để biểu diễn riêng ít nhất:

- `ffmpeg.available`
- `colmap.available`
- `cuda.available`, tên GPU, VRAM tổng và lỗi phát hiện nếu có
- `nerfstudio.train_available` dựa trên `ns-train`
- `nerfstudio.render_available` dựa trên `ns-render`
- `geometry.reconstruct_available`
- `geometry.train_available`
- `geometry.render_available`
- `geometry.available` chỉ khi toàn bộ dependency cần cho đường render geometry mục tiêu sẵn sàng
- `fallback_2_5d_lite.available`

Quy tắc:
- Không gộp “có lệnh” với “đã chạy được thành công”.
- Nếu cần kiểm tra runtime thực, cung cấp self-test riêng; không thực hiện training dài trong mỗi request capability.
- API response phải giữ ổn định và có reason/message có thể hiển thị cho người dùng.
- Frontend không tự suy luận capability chỉ từ tên GPU hoặc một cờ boolean chung.

### 6.2. Process runner

- [ ] Xây helper cho subprocess, dùng argument list thay vì ghép shell string.
- [ ] Hỗ trợ timeout theo loại tác vụ; timeout có cấu hình.
- [ ] Ghi stdout/stderr vào log theo job, giới hạn kích thước log trả qua API.
- [ ] Ghi command metadata đã làm sạch; không ghi secret.
- [ ] Bắt các trường hợp executable không tồn tại, exit code khác 0, timeout, signal termination và cancellation.
- [ ] Khi cancel, gửi terminate, chờ một khoảng hợp lý, rồi kill process tree nếu cần.
- [ ] Đảm bảo child process không sống sót sau khi worker/job bị hủy.
- [ ] Không đưa toàn bộ log có thể chứa đường dẫn/secret ra public response; cung cấp diagnostics đã lọc.

### Nghiệm thu

- Unit tests cover missing binary, non-zero exit, timeout, cancellation, stdout/stderr và đường dẫn có khoảng trắng.
- Capability endpoint phản ánh đúng môi trường CPU-only, COLMAP-only và GPU đầy đủ.
- Job lỗi có reason cụ thể thay vì treo mãi ở `processing`.

---

## 7. Phase 3 — Hoàn thiện pipeline geometry: ảnh → COLMAP → dataset

**Mục tiêu:** tái dựng camera/sparse geometry đáng tin cậy, không tự tạo dữ liệu giả.

### 7.1. COLMAP reconstruction

Tận dụng:
- `apps/api/app/services/geometry_backend.py`
- `packages/colmap/repository.py`
- `packages/geometry/nerfstudio.py`
- `packages/geometry/coords.py`
- `apps/api/app/services/scenes.py` nếu đây là nơi đang quản lý workspace/scene lifecycle.

Việc cần làm:
- [ ] Xác minh command COLMAP theo đúng version đã pin; không dựa vào cú pháp CLI không được kiểm thử.
- [ ] Workspace tách theo `project_id/scene_id/job_id`; không ghi đè scene hợp lệ khi một lần reconstruction mới thất bại.
- [ ] Lưu manifest đầu vào gồm asset ID, checksum, kích thước, thứ tự và cấu hình.
- [ ] Đọc số ảnh đầu vào, số ảnh registered, tỷ lệ registered, số camera, số sparse points, mean/median reprojection error nếu dữ liệu có sẵn, thời gian và exit code.
- [ ] Xử lý rõ các tình huống: ảnh trùng, ảnh không đọc được, không có feature, không đủ overlap, nhiều component tách rời, database/model không hoàn chỉnh.
- [ ] Quality gate có threshold cấu hình và được đánh giá trên benchmark; không hạ threshold để buộc mọi dataset pass.
- [ ] Giữ output thô và diagnostics đủ để điều tra lỗi; cleanup phải có chính sách retention.

### 7.2. Scene grouping

- [ ] Tích hợp `packages/scene_grouping/grouper.py` vào workflow phân tích/tạo scene.
- [ ] Ưu tiên evidence hình học: liên kết camera/feature, registered component, timestamp hoặc metadata tin cậy.
- [ ] Không gom hai vùng chỉ vì ngữ nghĩa giống nhau (ví dụ hai cây cầu khác nhau hoặc exterior và interior).
- [ ] Lưu lý do gom/tách, confidence, input evidence và cảnh báo khi dữ liệu không đủ.
- [ ] Cho phép người dùng xem và điều chỉnh nhóm ảnh trước khi chạy reconstruction tốn GPU.
- [ ] Bảo đảm asset ID thuộc đúng project và không thể tham chiếu asset của project khác.

### 7.3. Dataset Nerfstudio

- [ ] Xác minh `build_colmap_dataset` tạo đúng cấu trúc được version Nerfstudio hỗ trợ.
- [ ] Test camera model, intrinsics, extrinsics, image path, coordinate convention và up-axis.
- [ ] Viết round-trip tests cho `packages/geometry/coords.py`; dùng fixture pose có kết quả kỳ vọng đã tính trước.
- [ ] Không giả định camera convention của COLMAP và Nerfstudio giống nhau.
- [ ] Ghi phiên bản parser, schema và cấu hình chuyển đổi vào provenance.

### Nghiệm thu

- [ ] Dataset exterior-easy và interior-easy tái dựng thành công theo threshold đã chốt.
- [ ] sparse/disconnected dataset bị từ chối hoặc chia scene hợp lý; không bị quảng bá sai thành geometry tốt.
- [ ] Các số liệu reconstruction có thể tái tạo và truy ngược về asset đầu vào.
- [ ] Test coordinate conversion và dataset structure pass.

---

## 8. Phase 4 — Training/render 3DGS và tái sử dụng scene

**Mục tiêu:** dùng Nerfstudio/Splatfacto làm engine geometry chính ban đầu, không triển khai nhiều engine song song.

### Công việc

- [ ] Xác minh `ns-train` có trong capability và chạy được trong GPU worker.
- [ ] Pin profile training có tên/version, ví dụ Fast / Balanced / Detail; mọi tham số phải có nguồn gốc cấu hình.
- [ ] Trước khi train, kiểm tra CUDA, VRAM ước lượng, dung lượng ổ đĩa, số ảnh và chất lượng COLMAP.
- [ ] Huấn luyện trong workspace theo scene/version, ghi log và checkpoint path.
- [ ] Có progress theo stage thực tế; không nội suy % giả khi không có metric phù hợp. Có thể báo stage + elapsed time nếu engine không cung cấp progress tin cậy.
- [ ] Khi job lỗi, giữ diagnostics và cho phép retry với config mới mà không phá output đã hoàn tất.
- [ ] Xác định quy tắc reuse cache: cùng asset checksums + config + engine version có thể reuse; nếu khác thì tạo revision mới.
- [ ] Dùng `ns-render camera-path` hoặc entry point đã kiểm thử để render novel views.
- [ ] Chuyển đổi canonical CameraPathDocument sang định dạng engine ở một adapter; không để frontend viết trực tiếp định dạng Nerfstudio.
- [ ] Validate output frames: số frame, kích thước, định dạng, thứ tự và file cuối.
- [ ] Lưu model/config provenance để render có thể được tái tạo.
- [ ] Đo peak VRAM, RAM, thời gian training/render và chất lượng theo từng preset.

### Chất lượng hình học và giới hạn

- Sparse point cloud không phải mesh bề mặt hoàn chỉnh. Khoảng cách camera đến sparse points chỉ là **clearance proxy**, không chứng minh đường camera không va chạm vật thể.
- Nếu chưa có mesh/depth/occupancy đủ tin cậy, UI phải hiển thị giới hạn này; validator nên đưa confidence và rejection reason.
- Không dùng AI video generative để “sửa” hình học trong output kỹ thuật mà không có chế độ riêng và thông báo rõ.
- Nếu geometry render thất bại, fallback chỉ được chạy khi user/config cho phép và output phải mang mode/provenance đúng.

### Nghiệm thu

- [ ] Có ít nhất một clip geometry ngắn render thành công từ scene đã train.
- [ ] Camera path được đọc bởi engine đúng coordinate convention.
- [ ] Re-render cùng scene/config có thể tái tạo ở mức phù hợp; mọi sai khác do nondeterminism được ghi nhận.
- [ ] Chất lượng hình ảnh được đánh giá bằng review và metrics phù hợp, không chỉ bằng việc file được tạo.

---

## 9. Phase 5 — Camera path schema, keyframe editor và validator

**Mục tiêu:** người dùng chỉnh được chuyển động camera; API, frontend và backend dùng chung một schema.

### 9.1. Schema/API

Tận dụng `packages/geometry/camera_path.py` và `packages/geometry/keyframes.py`.

- [ ] Bổ sung hoặc hoàn thiện schema Pydantic cho camera path, keyframe, pose, quaternion, timestamp, easing và metadata.
- [ ] Thêm `schema_version` và quy tắc migration/validation.
- [ ] Xác định rõ đơn vị thời gian, hệ tọa độ, quy ước quaternion, hướng nhìn, FOV và trường optional.
- [ ] Thêm API GET/PUT cho camera path của shot/scene; dùng response model rõ ràng.
- [ ] Chặn timestamp trùng/âm, quaternion không hợp lệ, duration không khớp, giá trị NaN/Infinity, path quá lớn và số keyframe vượt giới hạn.
- [ ] Dùng optimistic concurrency/version nếu cần tránh hai lần cập nhật ghi đè nhau.
- [ ] Round-trip test: canonical JSON → parse → serialize phải giữ ngữ nghĩa.

### 9.2. Frontend editor

Xây trong `apps/web` theo từng bước:
1. Danh sách keyframe và thông tin thời gian.
2. Thêm/xóa keyframe.
3. Chọn keyframe, sửa thời gian/pose/FOV/easing qua form có validation.
4. Timeline scrubber hiển thị vị trí thời gian.
5. Camera preset: push-in, pull-out, orbit, reveal, fly-through — chỉ khả dụng nếu pose và geometry phù hợp.
6. Preview path và thông báo validator.
7. Save/load server, trạng thái unsaved changes và lỗi API.
8. Sau khi có viewer 3D đáng tin cậy, bổ sung đặt keyframe trực tiếp trong viewport.

### 9.3. Path validation

- [ ] Nối `packages/path_validation/validator.py` vào luồng render trước khi gọi engine.
- [ ] Validate continuity, tốc độ, gia tốc/độ mượt, bounds, duration, pose hợp lệ và clearance proxy nếu có dữ liệu.
- [ ] Trả về structured issues gồm code, severity, frame/time, metrics và lời khuyên sửa.
- [ ] Không chỉ trả một boolean; UI phải giải thích lý do reject/warning.
- [ ] Cho phép warning có thể tiếp tục chỉ khi policy cho phép; lỗi nghiêm trọng phải chặn render.
- [ ] Test các trường hợp path hợp lệ, quá nhanh, quaternion sai, outside bounds và thiếu geometry.

### Nghiệm thu

- [ ] Người dùng tạo, chỉnh, lưu và tải lại camera path.
- [ ] Render dùng đúng path vừa lưu, không dùng keyframe cũ.
- [ ] Validator hiển thị reason cụ thể và có unit tests.
- [ ] Có ít nhất một preset camera được benchmark trên exterior và interior scene.

---

## 10. Phase 6 — Render worker, job lifecycle, timeline và QC

**Mục tiêu:** mọi job đều có trạng thái chính xác, có thể điều tra, hủy và kiểm tra đầu ra.

### 10.1. Job state machine

Chuẩn hóa state transition, ví dụ:

`queued → processing → completed | failed | cancelled`

Có thể thêm `retry_wait` nếu retry policy yêu cầu. Quy định:
- [ ] Transition nào hợp lệ; job terminal không được tự quay lại processing.
- [ ] Claim job atomic/lease để Redis và DB polling không xử lý cùng job đồng thời.
- [ ] Worker heartbeat/last_seen và cơ chế phát hiện job bị kẹt.
- [ ] Retry chỉ cho lỗi tạm thời; lỗi input/quality/license/config không retry vô hạn.
- [ ] Retry có giới hạn, backoff và lưu attempt count.
- [ ] Cancel được kiểm tra giữa các stage và trong process dài nếu khả thi.
- [ ] Progress không giảm; từng stage báo message và timestamp.
- [ ] Job giữ error code/message đã lọc, log URI, input/output manifest và provenance.
- [ ] Đảm bảo DB session không bị dùng sai sau khi subprocess chạy lâu; test concurrency và session expiration.

### 10.2. Timeline assembly

- [ ] Xác định thứ tự shot ổn định, không dựa vào thứ tự DB không đảm bảo.
- [ ] Có API/schema quản lý thứ tự timeline hoặc trường sort index rõ ràng.
- [ ] Quy định transition, gap, duration, fps, resolution, subtitle và audio.
- [ ] Kiểm tra audio sample rate/duration, fade, subtitle encoding/font và đồng bộ tiếng/hình.
- [ ] Nếu shot render thất bại, không xuất video thành công bằng cách âm thầm bỏ shot; trả lỗi hoặc cho phép người dùng xác nhận phương án bỏ qua.
- [ ] Encode bằng FFmpeg qua argument list; quote đường dẫn an toàn, hỗ trợ tên file Unicode và đường dẫn có khoảng trắng.

### 10.3. Video quality control

Nâng cấp `qc_video_output` trong `apps/api/app/services/renderer.py`:

- [ ] File tồn tại, kích thước hợp lý và nằm trong output workspace cho phép.
- [ ] FFprobe đọc được container/streams.
- [ ] Video stream tồn tại, codec theo policy, pixel format tương thích trình duyệt (thường `yuv420p` cho H.264).
- [ ] Resolution đúng với yêu cầu.
- [ ] FPS và frame count hợp lệ; duration sai số trong ngưỡng cấu hình.
- [ ] Audio stream tồn tại khi yêu cầu có audio; nếu không yêu cầu thì không bắt buộc.
- [ ] Có thể bật decode smoke test cho final render hoặc benchmark.
- [ ] Lưu QC report có expected/actual values và lỗi.
- [ ] Chỉ chuyển job sang `completed` sau khi QC pass và output URI được xác minh.

### Nghiệm thu

- [ ] Cancel thực sự dừng job trong thời gian mục tiêu đã định.
- [ ] Job crash/restart không để trạng thái treo vô hạn.
- [ ] File hỏng, thiếu stream hoặc duration sai bị QC từ chối.
- [ ] Timeline có nhiều shot xuất đúng thứ tự, duration, subtitle/audio theo yêu cầu.
- [ ] Không thể download artifact của job/project không thuộc người dùng được phép truy cập (khi auth được bật).

---

## 11. Phase 7 — Hoàn thiện frontend thành công cụ làm video

**Mục tiêu:** UI phản ánh đúng khả năng backend và hỗ trợ luồng làm việc thực tế.

### Các khu vực UI cần hoàn thiện

1. **Project dashboard**
   - Danh sách, trạng thái, cập nhật gần nhất, số ảnh/scene/shot/job.
   - Empty/loading/error states rõ ràng.
   - Không nuốt lỗi API bằng `catch {}` mà không thông báo.

2. **Upload và Image QA**
   - Progress từng file, file thất bại, retry và tổng dung lượng.
   - Hiển thị resolution, sharpness/exposure, cảnh báo file trùng/ảnh chất lượng thấp.
   - Hỗ trợ cancel upload khi có thể.

3. **Scene manager**
   - Tạo scene từ tập asset đã chọn.
   - Hiển thị grouping, reconstruction status, confidence, metrics và rejection reasons.
   - Có nút reconstruction chỉ khi capability cho phép; nếu không, giải thích thiếu thành phần nào.
   - Cho phép người dùng đổi nhóm ảnh trước khi chạy tác vụ tốn tài nguyên.

4. **Shot/storyboard**
   - Chỉnh tên, asset IDs, mode, duration, fps, title/subtitle/narration.
   - Hiển thị mode thực tế sau khi server quyết định; không mặc định coi `auto` là Geometry.
   - Thêm thứ tự shot rõ ràng.

5. **Camera path**
   - Keyframe list, timeline, validation panel, presets, save state và preview.
   - Chặn lưu nếu schema invalid và báo field nào sai.

6. **Render jobs**
   - Poll có backoff và dừng khi job terminal; tránh interval bị tạo lại liên tục vì object state thay đổi.
   - Hiển thị stage, progress, elapsed time, cancel, retry nếu được phép, log summary và QC.
   - Khi hoàn tất, kiểm tra download URI và hiển thị mode, resolution, duration, codec.

7. **Accessibility / UX**
   - Form label, keyboard navigation, trạng thái focus, thông báo lỗi có thể đọc.
   - Tránh thao tác chỉ có màu sắc để truyền đạt trạng thái.
   - Giao diện responsive; không cần làm đẹp trước khi luồng nghiệp vụ chính xác.

### Nghiệm thu

- Có thể hoàn thành luồng chính từ project mới tới video tải xuống chỉ bằng UI.
- Mọi lỗi backend quan trọng được hiển thị; không có nút “thành công giả”.
- UI không cho phép người dùng tạo request thiếu dữ liệu bắt buộc.
- Test thủ công có checklist và ảnh chụp/log khi nghiệm thu release.

---

## 12. Phase 8 — Storage, bảo mật và độ bền dữ liệu

**Mục tiêu:** sẵn sàng cho nhiều project và chuyển đổi local → cloud mà không viết lại toàn bộ nghiệp vụ.

### 12.1. Storage abstraction

Tận dụng `apps/api/app/services/storage.py` và biến môi trường hiện có.

- [ ] Mọi service dùng storage URI/logical key, không tự nối path tuyệt đối.
- [ ] Local storage vẫn là backend mặc định cho local development.
- [ ] Thiết kế adapter cho S3-compatible object storage; không hard-code một vendor.
- [ ] Phân biệt immutable input assets, intermediate artifacts, reusable scene artifacts và final outputs.
- [ ] Định nghĩa retention/cleanup theo loại artifact và trạng thái job.
- [ ] Dùng checksum để phát hiện upload trùng và xác minh file.
- [ ] Thực hiện ghi an toàn: temporary path → validate → atomic move/commit metadata.
- [ ] Không xóa artifact đang được job khác sử dụng.

### 12.2. Upload và API security

- [ ] Giới hạn kích thước file, số lượng file, tổng dung lượng project và loại file.
- [ ] Không tin extension hoặc client MIME; xác minh nội dung bằng decoder phù hợp.
- [ ] Tạo tên lưu trữ nội bộ; không dùng tên client để tạo path trực tiếp.
- [ ] Chặn path traversal và kiểm tra mọi storage key.
- [ ] Có timeout và quota để ngăn người dùng gửi hàng nghìn ảnh hoặc render vô hạn.
- [ ] Khi đưa lên Internet, thêm authentication, authorization theo project, rate limiting, CORS allowlist và secret management.
- [ ] Endpoint download phải kiểm tra quyền sở hữu trước khi trả file hoặc signed URL.
- [ ] Không trả stack trace, secret hoặc đường dẫn nội bộ trong response public.
- [ ] Có backup/restore cho database và object storage; thử restore chứ không chỉ tạo backup.

### Nghiệm thu

- [ ] Test file sai định dạng, file quá lớn, tên Unicode, tên chứa ký tự đặc biệt, path traversal và upload trùng.
- [ ] Storage backend local có test; object storage chỉ được tuyên bố hỗ trợ sau integration test thật.
- [ ] Có chính sách cleanup và test không xóa nhầm artifact đang sử dụng.

---

## 13. Phase 9 — Chạy thật trên GPU công ty và benchmark

**Đây là gate bắt buộc trước khi đầu tư vào cloud GPU.**

### 13.1. Môi trường GPU cần ghi nhận

- OS và version driver NVIDIA.
- GPU model, VRAM tổng và VRAM trống lúc bắt đầu.
- CUDA runtime, PyTorch version và `torch.cuda.is_available()`.
- COLMAP version và lệnh dùng.
- Nerfstudio, gsplat, `ns-train`, `ns-render` version/path.
- FFmpeg/FFprobe version và encoder.
- Git commit SHA, cấu hình engine, số ảnh, resolution đầu vào.
- Không đưa secret hoặc dữ liệu riêng tư vào report.

### 13.2. Bộ benchmark bắt buộc

Dùng `docs/BENCHMARK_DATASETS.md` làm manifest chính. Tạo dataset versioned có quyền sử dụng phù hợp:

| Dataset ID | Kỳ vọng | Điều phải chứng minh |
|---|---|---|
| `exterior-easy-v1` | Geometry | Ảnh có overlap, camera registered, 3DGS train/render và MP4 QC pass |
| `interior-easy-v1` | Geometry | Tái dựng phòng có texture và baseline vừa phải; camera path không xuyên/nhảy bất thường theo evidence có sẵn |
| `sparse-v1` | Fallback/reject | Thiếu overlap bị giải thích rõ; không quảng cáo geometry thành công |
| `single-image-v1` | 2.5D | Chỉ tạo chuyển động 2D bảo thủ, gắn nhãn đúng |
| `disconnected-v1` | Tách scene/fallback | Exterior và interior không bị ghép thành một scene hình học sai |

Mỗi lần chạy phải lưu:
- dataset version và manifest/checksum;
- số ảnh input, số ảnh registered và tỷ lệ registered;
- reconstruction/train/render/encode time;
- peak VRAM và RAM;
- engine/config versions;
- output artifact và QC report;
- pass/fail, lý do fail và log;
- nhận xét chất lượng hình học bằng review trực quan.

### 13.3. Cổng nghiệm thu

- [ ] Exterior benchmark pass.
- [ ] Interior benchmark pass.
- [ ] Sparse dataset bị reject/fallback đúng.
- [ ] Single-image mode không tạo claim 3D.
- [ ] Disconnected dataset không bị nối geometry một cách sai lệch.
- [ ] Một video geometry ngắn xuất thành công trên máy GPU công ty.
- [ ] Đã đo thời gian và tài nguyên; không ước lượng bằng cảm tính.
- [ ] `docs/PHASE0_CHECKLIST.md` và `docs/PROJECT_STATUS.md` được cập nhật theo bằng chứng.

Không chuyển sang hybrid GPU router trước khi gate này đạt.

---

## 14. Phase 10 — Local GPU agent và cloud GPU worker

Chỉ thực hiện sau Phase 9. Kiến trúc phải cho phép người dùng chọn xử lý local hoặc remote mà không làm thay đổi schema nghiệp vụ.

### 14.1. Local GPU agent

- [ ] Định nghĩa protocol có version giữa web/API và agent.
- [ ] Agent đăng ký capability, GPU, VRAM, engine version và heartbeat.
- [ ] Job payload chỉ chứa job ID, artifact references, config và authorization ngắn hạn; không gửi secret không cần thiết.
- [ ] Agent tải input từ storage được cấp quyền, chạy job, upload output/log/provenance.
- [ ] Có lease, timeout, cancel, retry, idempotency key và xử lý agent offline.
- [ ] Không mở cổng inbound công khai trên máy công ty nếu có thể dùng outbound secure connection.
- [ ] Ký hoặc xác thực agent; TLS, credential rotation và giới hạn quyền theo job.
- [ ] Cho phép user biết file nào sẽ được gửi ra khỏi máy local.

### 14.2. Cloud GPU worker

- [ ] Tách API/control plane khỏi GPU data plane.
- [ ] Job scheduler chọn worker theo capability, VRAM, queue depth, chi phí và vùng dữ liệu.
- [ ] Worker image pin theo digest/version; benchmark trước khi đổi image.
- [ ] Object storage dùng signed URL có thời hạn hoặc quyền service-to-service.
- [ ] Theo dõi chi phí theo job, giới hạn quota và timeout.
- [ ] Có xử lý worker chết giữa chừng, checkpoint/retry nếu engine hỗ trợ.
- [ ] Có chính sách xóa dữ liệu và bảo mật thông tin dự án.
- [ ] Hiển thị chi phí ước tính trước khi submit nếu người dùng phải trả tiền.

### 14.3. Không làm ở giai đoạn đầu

- Không xây GPU marketplace/billing trước khi pipeline core ổn định.
- Không tự động gửi dữ liệu công trình nhạy cảm lên cloud khi chưa có consent.
- Không hứa hẹn “chạy trên mọi GPU”; cần capability matrix và benchmark cho từng loại runtime.

---

## 15. Kiểm thử: tầng, phạm vi và điều kiện release

### 15.1. Unit tests

Tập trung vào:
- Camera math, quaternion normalization/SLERP, easing và interpolation.
- Canonical camera path serialization/versioning.
- Coordinate conversion COLMAP ↔ canonical ↔ Nerfstudio.
- Keyframe selection.
- Scene grouping với dữ liệu liên kết và dữ liệu disconnected.
- Path validator và structured rejection reasons.
- Capability detection với executable giả lập/missing dependency.
- Process runner: timeout, cancel, non-zero exit, output capture.
- Video QC parsing và rule validation.
- Storage URI/key safety.

### 15.2. API/integration tests

- Project CRUD và ownership checks.
- Upload, hash, QA, giới hạn file.
- Scene creation, reconstruction job creation và status transition.
- Shot/camera path create-read-update-validate.
- Preview/timeline job lifecycle.
- Cancel/retry behavior.
- Download permissions và missing artifact.
- API response schema và error contracts.

### 15.3. End-to-end tests

- CPU-only: upload một ảnh → QA → 2.5D render → MP4 → FFprobe QC → download.
- Geometry-capable: benchmark exterior → COLMAP → dataset → training → camera path → render → encode → QC.
- Negative geometry: sparse/disconnected data → rejection/fallback có lý do.
- Worker restart giữa job và queue/DB consistency.
- Tên file Unicode, đường dẫn có khoảng trắng và nhiều job đồng thời.

### 15.4. CI tối thiểu

- Lint/format theo tooling đã chọn.
- Type check frontend.
- Unit + API tests không cần GPU.
- Build web/API Docker images.
- Kiểm tra package import.
- License/dependency audit theo policy.
- Geometry GPU benchmark có thể chạy ở runner chuyên dụng hoặc thủ công có artifact; không giả pass nếu CI không có GPU.

### 15.5. Release gate

Không phát hành nếu:
- tests chính thất bại;
- API/worker Docker image không build hoặc không khởi động;
- output MP4 không qua QC;
- job có thể kẹt vô hạn;
- lỗi geometry bị che hoặc bị báo thành công;
- dependency/model license còn `BLOCKED` đối với mục đích phân phối thương mại.

---

## 16. License và quản lý repository tham khảo

Các nguồn ngoài chỉ là tham khảo có chọn lọc. Trước khi sao chép code, model, checkpoint, binary hoặc asset:
- [ ] Ghi URL repo, commit SHA/tag, file được xem xét và license.
- [ ] Kiểm tra license của dependency transitive, model/checkpoint và binary; license repo chính không tự động áp dụng cho tất cả.
- [ ] Ghi quyền sử dụng thương mại, phân phối lại, notice và điều kiện attribution.
- [ ] Cập nhật `docs/DEPENDENCY_LICENSE_GATE.md`.
- [ ] Nếu license không phù hợp hoặc chưa rõ, không copy code; triển khai clean-room dựa trên hành vi/tài liệu được phép hoặc tìm giải pháp khác.
- [ ] Không copy code từ dự án GPL vào core nếu mô hình phân phối dự kiến không tương thích; tham khảo ý tưởng UI/UX bằng implementation độc lập.
- [ ] Giữ SBOM/dependency lock và thông báo third-party cần thiết khi chuẩn bị release.

Nguồn ưu tiên để tham khảo:
- [Nerfstudio](https://github.com/nerfstudio-project/nerfstudio): engine, dataset, Splatfacto, camera path.
- [COLMAP](https://github.com/colmap/colmap): SfM, registered cameras và sparse point cloud.
- [Scene-Gaussian-Splat-Viewer](https://github.com/iab131/Scene-Gaussian-Splat-Viewer): UI pattern cho timeline/keyframes; kiểm tra license trước khi copy.
- [OOOSplat](https://github.com/ooolabdev/ooosplat): pipeline stages/progress/cancel/resume; không thay thế worker hiện có.
- [KIRI-Maker](https://github.com/willjim/KIRI-Maker): tham khảo camera presets và chuyển động cinematic; kiểm tra license, phiên bản và tính khả thi trước khi dùng.
- [FFmpeg](https://github.com/FFmpeg/FFmpeg): encode và xử lý video; ghi nhận build flags/codec.

Không tích hợp tất cả các repo trên cùng lúc. Engine chính ban đầu là COLMAP + Nerfstudio/Splatfacto; repo còn lại chỉ được sử dụng nếu giải quyết được vấn đề cụ thể và vượt test/benchmark.

---

## 17. Thứ tự ưu tiên và phụ thuộc

| Ưu tiên | Hạng mục | Phụ thuộc | Kết quả cần có |
|---|---|---|---|
| P0 | Baseline + status report | Không | Biết chính xác trạng thái code/test |
| P0 | Package/Docker fixes | Baseline | CPU API/worker build và import ổn định |
| P0 | Capability + process runner | Package baseline | Lỗi môi trường và subprocess được xử lý |
| P0 | COLMAP + dataset + quality gate | Capability/runner | Reconstruction có diagnostics |
| P0 | Nerfstudio training/render | COLMAP output + GPU | Geometry clip thực tế |
| P0 | FFprobe QC + job lifecycle | Renderer/worker | Job chỉ complete khi artifact hợp lệ |
| P0 | GPU benchmark | Pipeline E2E | Gate geometry được xác minh |
| P1 | Camera path API/editor | Schema/engine adapter | Chỉnh camera path từ UI |
| P1 | Scene grouping UI | COLMAP diagnostics | Tổ chức scene chính xác hơn |
| P1 | Storage hardening/auth | Core data flow | Dữ liệu được kiểm soát an toàn |
| P2 | Object storage | Storage abstraction | Chuyển storage không viết lại nghiệp vụ |
| P2 | Local GPU agent | GPU benchmark + protocol | Dùng GPU local qua web an toàn |
| P2 | Cloud GPU worker | Object storage + scheduler | Render remote có chi phí/giám sát |
| P3 | Nhiều engine, AI enhancement | Benchmark/UX đã ổn định | Chỉ thêm khi có use case và gate riêng |

**Nguyên tắc:** làm xong một hạng mục P0 và chứng minh bằng test trước khi mở rộng P1/P2. Không làm UI nâng cao hoặc marketplace để né việc geometry pipeline chưa chạy thật.

---

## 18. Kế hoạch thực hiện theo pull request nhỏ

Đề xuất tách thành các PR/commit có phạm vi rõ ràng:

1. **PR-01 — Baseline & documentation:** cập nhật trạng thái repo, lệnh chạy/test, môi trường và blocker.
2. **PR-02 — Python packaging & CPU Docker:** fix import packages, build image, startup API/worker.
3. **PR-03 — GPU image cleanup:** một base image, dependency pin, capability self-test.
4. **PR-04 — Capability/process runner:** timeout, cancel, logging và reason codes.
5. **PR-05 — Geometry integration tests:** COLMAP fixture, parser, coordinate conversion và dataset builder.
6. **PR-06 — Reconstruction quality gate:** thresholds, diagnostics, rejection cases, benchmark fixtures.
7. **PR-07 — Nerfstudio train/render adapter:** config profile, cache/provenance, output frame checks.
8. **PR-08 — FFprobe QC:** validate codec/resolution/fps/duration/streams và chỉ complete sau QC.
9. **PR-09 — Job lifecycle hardening:** atomic claim, retry, heartbeat, cancel, stuck-job recovery.
10. **PR-10 — Camera path API:** schema version, CRUD, validation và round-trip tests.
11. **PR-11 — Camera path editor UI:** keyframes, timeline, presets, validation feedback.
12. **PR-12 — Scene grouping integration/UI:** evidence, confidence và user correction.
13. **PR-13 — Security/storage hardening:** upload limits, path safety, permissions, cleanup.
14. **PR-14 — GPU benchmark report:** kết quả end-to-end, thời gian, VRAM, output, quality review.
15. **PR-15+ — Local agent/cloud worker:** chỉ bắt đầu khi PR-14 đạt gate và có yêu cầu triển khai rõ ràng.

Tên PR có thể thay đổi theo workflow thực tế; không gộp tất cả vào một thay đổi lớn khó review.

---

## 19. Prompt chuẩn cho coding agent

Dùng prompt dưới đây cho từng phase. Thay `[PHASE]` bằng một phase cụ thể; không yêu cầu agent làm tất cả cùng lúc.

```text
Bạn đang làm việc trong repository hieudang99dd/AI-Video-.

Đọc trước:
- docs/KE_HOACH_HOAN_THIEN_REPO.md
- docs/PHASE0_CHECKLIST.md
- docs/BENCHMARK_DATASETS.md
- docs/DEPENDENCY_LICENSE_GATE.md
- SKILL_CANONICAL.md (nếu tồn tại)

Nhiệm vụ: chỉ triển khai [PHASE] và các phụ thuộc trực tiếp cần thiết.

Quy tắc bắt buộc:
1. Kiểm tra branch, git status và code hiện tại trước khi sửa.
2. Không viết lại thành phần đã tồn tại; ưu tiên sửa/hoàn thiện đúng module hiện tại.
3. Trước khi tạo abstraction mới, tìm nơi abstraction hiện tại đang được dùng.
4. Không giả lập kết quả COLMAP/3DGS, không đánh dấu geometry pass nếu chưa chạy thật.
5. Không thêm dependency/repository/model mới nếu chưa giải thích lý do, version và license.
6. Thêm hoặc cập nhật test cho mọi hành vi mới; không sửa/xóa test chỉ để làm CI xanh.
7. Không commit ảnh, checkpoint, model weights, video hoặc artifact lớn.
8. Không thay đổi API/schema mà không cập nhật contract và test tương ứng.
9. Với subprocess: xử lý timeout, exit code, log, cancellation và đường dẫn an toàn.
10. Giữ thay đổi nhỏ; không thực hiện refactor ngoài phạm vi.

Quy trình:
A. Tóm tắt code hiện tại và các file dự định sửa.
B. Liệt kê rủi ro, giả định và tiêu chí nghiệm thu.
C. Triển khai thay đổi nhỏ theo từng bước.
D. Chạy test phù hợp, ghi chính xác lệnh và kết quả.
E. Nếu test cần GPU hoặc dependency chưa có, đánh dấu BLOCKED; không giả pass.
F. Cập nhật tài liệu trạng thái và cấu hình nếu cần.
G. Báo cáo cuối: file đổi, lý do, test pass/fail, blocker, lệnh để người dùng xác minh.

Không bắt đầu phase tiếp theo nếu phase hiện tại chưa đạt tiêu chí nghiệm thu hoặc chưa nêu rõ blocker.
```

### Prompt dành riêng cho kiểm tra end-to-end GPU

```text
Hãy xác minh pipeline geometry end-to-end trên máy GPU này, không sửa rộng repo trước khi có baseline.

1. Ghi OS, driver, GPU/VRAM, CUDA/PyTorch, COLMAP, Nerfstudio, gsplat, FFmpeg/FFprobe và commit SHA.
2. Chạy capability check và kiểm tra import.
3. Dùng dataset benchmark có quyền sử dụng; ghi checksum/manifest.
4. Chạy upload/scene -> COLMAP -> quality gate -> Nerfstudio training -> camera path -> frame render -> MP4 encode -> FFprobe QC.
5. Lưu log, thời gian mỗi stage, registered ratio, peak VRAM/RAM, cấu hình và output.
6. Chạy negative test với sparse/disconnected data để xác nhận reject/fallback đúng.
7. Nếu fail, phân loại lỗi và đề xuất sửa nhỏ nhất; không hạ threshold chỉ để pass.
8. Cập nhật docs/PHASE0_CHECKLIST.md và docs/PROJECT_STATUS.md theo bằng chứng.
9. Không tuyên bố VERIFIED ON GPU nếu chưa tạo được output và QC report thật.
```

---

## 20. Checklist release cuối cùng

### Core functionality
- [ ] Tạo project và upload ảnh ổn định.
- [ ] Image QA có kết quả và cảnh báo rõ.
- [ ] Scene grouping dựa trên evidence và có thể điều chỉnh.
- [ ] COLMAP reconstruction có diagnostics và quality gate.
- [ ] Nerfstudio/Splatfacto train/render trên GPU mục tiêu.
- [ ] Camera path canonical có thể chỉnh từ API/UI.
- [ ] Path validator chạy trước geometry render.
- [ ] 2.5D fallback được gắn nhãn chính xác.
- [ ] Timeline assembly theo thứ tự ổn định.
- [ ] MP4 qua FFprobe/QC trước khi job complete.

### Reliability
- [ ] Docker CPU build và startup pass.
- [ ] GPU image và runtime check pass trên GPU hỗ trợ.
- [ ] Job timeout/cancel/retry/restart được test.
- [ ] Job lỗi không bị treo hoặc báo thành công.
- [ ] Storage cleanup không xóa artifact đang dùng.
- [ ] Logs/provenance đủ để điều tra lỗi.

### Security and operations
- [ ] Upload validation, quota và path safety.
- [ ] Authentication/authorization trước khi mở Internet.
- [ ] Download endpoint kiểm tra quyền.
- [ ] Secrets không nằm trong Git/log.
- [ ] Backup/restore đã thử.
- [ ] Dependency/model license được duyệt cho mục đích triển khai.
- [ ] Có hướng dẫn cài đặt, chạy, cập nhật và xử lý sự cố.

### Evidence
- [ ] Unit/API/E2E tests có báo cáo.
- [ ] Exterior benchmark pass.
- [ ] Interior benchmark pass.
- [ ] Sparse/single-image/disconnected negative cases đúng kỳ vọng.
- [ ] Video output và QC report có thể truy cập.
- [ ] `docs/PHASE0_CHECKLIST.md`, `docs/BENCHMARK_DATASETS.md`, `docs/PROJECT_STATUS.md` phản ánh trạng thái thực tế.

---

## 21. Hướng dẫn vận hành và xử lý sự cố cần bổ sung vào README

README nên cung cấp các lệnh chính xác đã được kiểm tra trên repo:

- Cài đặt môi trường CPU/local.
- Khởi động API, worker, web và database.
- Chạy unit/API tests.
- Build và chạy Docker CPU.
- Build/chạy GPU worker trên máy có NVIDIA GPU.
- Kiểm tra capability và phiên bản dependency.
- Chạy một benchmark end-to-end.
- Xem log theo job và tìm artifact/QC report.
- Khôi phục job bị kẹt, retry hoặc hủy job.
- Backup/restore database và storage.
- Khắc phục các lỗi thường gặp:
  - `ModuleNotFoundError: packages.*`
  - không tìm thấy COLMAP / `ns-train` / `ns-render`
  - CUDA không khả dụng hoặc hết VRAM
  - COLMAP đăng ký quá ít ảnh
  - camera coordinate bị đảo hoặc hướng trục sai
  - FFmpeg/FFprobe không đọc được output
  - worker không lấy job từ Redis/DB
  - job hoàn tất nhưng artifact không tồn tại.

Không đưa lệnh vào README cho đến khi đã chạy hoặc đánh dấu rõ là ví dụ chưa xác minh.

---

## 22. Quyết định kỹ thuật còn cần chốt

Không tự đoán các quyết định sau; ghi lại quyết định và lý do trong tài liệu hoặc ADR ngắn:

1. Phiên bản chính thức của Python, PyTorch, CUDA, Nerfstudio và gsplat.
2. Ngưỡng chất lượng reconstruction theo từng loại dataset.
3. Chính sách retry, timeout và giới hạn tài nguyên cho từng job type.
4. Schema camera path/version migration.
5. Quy tắc giữ/xóa intermediate artifacts và checkpoints.
6. Storage cloud được hỗ trợ đầu tiên (nếu/ khi triển khai).
7. Authentication/authorization provider khi mở Internet.
8. GPU mục tiêu tối thiểu và preset Fast/Balanced/Detail.
9. Định nghĩa rõ mode nào bảo toàn hình học và mode nào chỉ mang tính minh họa.
10. License/commercial-use decision cho từng dependency/model/binary.

Mỗi quyết định nên có: bối cảnh, lựa chọn, ưu/nhược điểm, quyết định, ngày và cách kiểm chứng.

---

## 23. Kết luận triển khai

Thứ tự đúng để hoàn thiện AI-Video- là:

**Đóng gói chạy ổn định → capability/process runner đáng tin cậy → COLMAP reconstruction → Nerfstudio/Splatfacto → camera path → render + FFprobe QC → benchmark GPU thật → UI editor → storage/security → local/cloud GPU.**

Nếu chỉ chọn một mục tiêu gần nhất, hãy hoàn thành **Phase 1 đến Phase 4**, sau đó chạy benchmark geometry trên máy GPU công ty. Đây là điểm quyết định dự án có nền tảng 3D thật hay chỉ là công cụ chuyển động ảnh 2D. Chỉ mở rộng cloud/marketplace sau khi có bằng chứng end-to-end.

> **Quy tắc báo cáo cuối cùng:** phân biệt rõ “đã viết code”, “test tự động pass”, “đã build container”, và “đã VERIFIED ON GPU”. Đây là bốn trạng thái khác nhau và không được dùng thay thế cho nhau.
