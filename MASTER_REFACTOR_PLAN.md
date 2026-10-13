# AI-VIDEO — MASTER REFACTOR & DELIVERY PLAN
> **Canonical / Single Source of Truth** — quy trình đại phẫu repository từ prototype đến sản phẩm có thể nghiệm thu và vận hành thực tế.
>
> **Repository:** https://github.com/hieudang99dd/AI-Video-
>
> **Baseline audit:** nhánh `main`, commit `87cc55241198d3654246ff3943a4c99c8b303063`, kiểm tra ngày 2026-10-13 (ICT).
>
> **Tài liệu:** v1.0 — planning/architecture approval. **Đây là kế hoạch triển khai, KHÔNG khẳng định các phase đã hoàn thành.**
>
> **Phạm vi:** ảnh tĩnh JPG/PNG/WebP từ Civil 3D / InfraWorks → video hạ tầng có camera có kiểm soát, giữ tính nhất quán hình học theo khả năng dữ liệu, cinematic tùy chọn, MP4; Windows/local trước, nhiều người dùng sau.

---

## 0. Quy tắc đọc và thẩm quyền tài liệu

1. **Tài liệu này là nguồn chuẩn duy nhất** cho thứ tự phase, nguyên tắc kỹ thuật, tiêu chí nghiệm thu và phân loại tình trạng tính năng.
2. `SKILL_CANONICAL.md` và `docs/skills/*` chỉ là tài liệu tham khảo nghiệp vụ/thuật toán lịch sử; khi xung đột với tài liệu này, **ưu tiên tài liệu này**. Không âm thầm xóa dữ liệu lịch sử.
3. `PROJECT_STATUS.md` là sổ trạng thái thực hiện và bằng chứng; cập nhật sau mỗi PR/phase; không dùng làm spec thứ hai.
4. `README.md` chỉ chứa định vị sản phẩm, quickstart đã kiểm chứng và liên kết tài liệu chuẩn.
5. `docs/ARCHITECTURE.md` trình bày kiến trúc **đang triển khai**; diagram **mục tiêu** nằm trong tài liệu này. Nếu code và docs khác nhau, ghi `DEVIATION`, mở issue, không sửa tài liệu để tô hồng code.
6. **Cấm làm giả:** screenshot mock, point cloud mô phỏng, AI job copy-file, score ngẫu nhiên, script chỉ được xuất chứ chưa chạy, test mock dịch vụ bên ngoài không được gắn nhãn `verified_live`.
7. Trạng thái bắt buộc: `NOT_IMPLEMENTED` / `SCAFFOLDED` / `UNIT_TESTED` / `INTEGRATION_TESTED` / `HARDWARE_VERIFIED` / `PRODUCTION_READY`. Mỗi tuyên bố trạng thái phải đi kèm artifact/log/test run/version.
8. **Không tự xác nhận độ chính xác thiết kế:** ảnh tĩnh không chứa đầy đủ hình học, kích thước, hệ tọa độ, bề mặt khuất. Chỉ có thể xây dựng **ước lượng 3D** khi ảnh đủ chồng phủ và chất lượng. Không biến ước lượng thành dữ liệu kỹ thuật có giá trị đo đạc.
9. **Thay đổi cấu trúc toàn diện được cho phép**, nhưng cần migration, test và rollback. Không xóa code cũ cho đến khi thay thế chạy được với dữ liệu thật.
10. Agent được quyền sửa/refactor/add/delete code, thư mục, endpoint, schema, UI và Dockerfile trong các PR riêng có log thay đổi. Không tự xóa dữ liệu người dùng, secrets, history Git hay force-push nhánh chính.

## 1. Tầm nhìn sản phẩm và giới hạn bắt buộc

### 1.1. Sản phẩm phải giải quyết

- Kỹ sư tải 1–N ảnh từ Civil 3D/InfraWorks; kiểm tra chất lượng, duplicate, overlap, shot types, thứ tự theo lý trình nếu được cung cấp.
- Tự tạo storyboard theo hạng mục: toàn cảnh, đường, cầu, nút giao, thoát nước, taluy, mặt cắt; người dùng có thể sửa hoàn toàn.
- **Chế độ C – Source Image 2D:** dùng ảnh gốc, pan/zoom/crop/crossfade theo timeline; có thể render CPU và xuất MP4; **không gọi là bay camera 3D**.
- **Chế độ B – Ordered Images:** nhiều ảnh có thứ tự, nội suy và chuyển cảnh; có thể dùng 2.5D an toàn nếu có depth layers; **không đồng nghĩa novel-view chính xác**.
- **Chế độ A – Reconstructed 3D:** COLMAP (hoặc backend hợp lệ) → scene chất lượng đạt gate → camera theo pose/geometry → Nerfstudio/Blender/renderer thực → video; nếu thất bại phải hiển thị lý do và fallback rõ ràng.
- Cho phép người dùng kéo keyframe camera trên viewport thật, xem preview camera path/point cloud/mesh thật, sửa FOV, độ cao, tốc độ, easing.
- AI video (Wan2.2, MoVerse hoặc provider khác) **chỉ tùy chọn**, có inference thực, cost/VRAM gate và nguồn frame thực để so sánh; luôn giữ bản gốc và cơ chế revert.
- Xuất MP4 H.264/H.265 tùy profile, audio/title/caption, báo cáo provenance/quality/limitations. Người dùng có thể mở lại project và reproducibly render lại.

### 1.2. Không hứa những điều ảnh tĩnh không đáp ứng

- Không thể khôi phục chính xác 100% model CAD/BIM, bề mặt khuất, số làn xe hoặc vật thể không hiện ra từ ảnh.
- Không thể đảm bảo camera tự bay mọi góc như Twinmotion nếu không có scene 3D chất lượng.
- SfM có scale ambiguity: dùng `uncalibrated`, `relative_units` trừ khi có ground control/dimensions/metadata đủ kiểm tra.
- Video AI sinh có thể bóp méo kết cấu; chỉ minh họa điện ảnh, không chứng minh đúng thiết kế.
- **Gói ảnh chụp từ cùng một camera, mỗi ảnh khác dự án, ảnh render ít texture hoặc góc nhìn rời rạc** phải được phát hiện và định tuyến về B/C thay vì ép A.

### 1.3. Đầu ra bắt buộc

- Video file thực: `.mp4` (codec, FPS, resolution, duration có thể xác minh bằng ffprobe).
- `project_manifest.json`, `shot_manifest.json`, `camera_path.json`, `quality_report.json`, `provenance.json`, logs có redaction và sha256 artifacts.
- Với A-mode có thể có `COLMAP sparse model`, `camera poses`, `3DGS training checkpoint` hoặc `mesh/point-cloud`.
- Báo rõ: `render_backend_requested`, `render_backend_effective`, `fallback_reason`, `ai_applied_verified`.

---

## 2. Kết quả audit repo hiện có — lỗi, nguyên nhân, bằng chứng, ưu tiên

**Phân loại:** P0 = làm sai kết quả/an toàn/block triển khai; P1 = ngăn sản phẩm dùng thực chiến; P2 = tối ưu/mở rộng. Các bằng chứng là **đọc mã tĩnh tại baseline**; nơi cần chạy test/live phải ghi chưa nghiệm thu.

| ID | Mức | Phát hiện từ source | File/điểm gốc | Sửa gì / nghiệm thu |
|---|---|---|---|---|
| BUG-001 | **P0** | GitHub Pages tạo Edge IoU/SSIM/temporal score bằng `Math.random()`; tuyên bố QC đạt không có phép đo | `index.html`, `runShotAIEnhancementQC` | Xóa random score; lấy QC từ API hoặc hiện `NOT_RUN`; test screenshot/state |
| BUG-002 | **P0** | API QC so sánh cùng danh sách `image_paths` cho cả original và AI | `apps/api/app/api/routes.py`, `run_shot_ai_enhancement` | Trích frame từ **2 video khác nhau**, đồng bộ timestamp, fail-closed khi thiếu nguồn |
| BUG-003 | **P0** | `Wan22Adapter.enhance_render` chỉ `shutil.copy2` và có thể mô tả diffusion là đã thực thi | `apps/api/app/services/ai_adapter.py` | Provider worker inference thật, hoặc `NOT_IMPLEMENTED`; không dán nhãn `AI_ENHANCED` khi copy |
| BUG-004 | **P0** | Endpoint tạo `AIJob(status="completed")` dù có nhánh không có source render và không chạy inference | `apps/api/app/api/routes.py` | Tạo job queue có trạng thái thật, artifacts + checksum + log kiểm chứng; không completed rỗng |
| BUG-005 | **P0** | API endpoints create/list/download thiếu authn/authz theo project; CORS `*` | `apps/api/app/main.py`, `routes.py` | Auth/session, project ownership, deny cross-tenant, CORS allowlist, test IDOR |
| BUG-006 | **P0** | Container API COPY `apps/api/app` nhưng không COPY `packages`; imports `packages.*` có nguy cơ làm container không khởi động | `apps/api/Dockerfile` | Chạy clean Docker build + health + smoke; packaging/monorepo rõ ràng |
| BUG-007 | **P0** | Dockerfile GPU có nhiều `FROM`/install Nerfstudio lặp và `COPY scripts` không tương ứng cây root; chưa có clean GPU build chứng minh | `apps/api/Dockerfile.gpu` | 1 image GPU reproducible, lock dependency, smoke CLI/CUDA |
| BUG-008 | **P0** | Storage upload ghi liên tục đến EOF; limit của hàm validate không nhận byte count tại route; kiểm tra extension chưa kiểm tra magic/decode/pixel limit | `storage.py`, `routes.py`, `job_manager.py` | Count bytes khi stream, reject oversize, atomic temp→rename, Pillow verify/decompression bomb checks |
| BUG-009 | **P0** | In-process `/render-jobs/{id}/run-now` gọi process trực tiếp trong request, trái với hướng async worker; dễ block server | `routes.py` | Chỉ cho dev flag; production enqueue/poll/events; test timeout |
| BUG-010 | **P1** | Job claim bằng SELECT queued rồi đổi status, thiếu atomic claim/lock; dedup key đã viết nhưng chưa áp dụng tại route | `render_worker.py`, `job_manager.py`, `routes.py` | DB unique/idempotency + lease/heartbeat/retry + exactly-one effective artifact |
| BUG-011 | **P1** | `transition_job_state` log warning khi illegal transition nhưng vẫn buộc chuyển state | `job_manager.py` | State machine strict, CAS transition, tests concurrent |
| BUG-012 | **P1** | Blender script có thể sinh, nhưng render worker gọi `execute_if_available=False` | `render_worker.py` | Backend choice cho Blender thật; thử render headless và xác minh artifact |
| BUG-013 | **P1** | Blender đặt ảnh lên plane có khoảng cách cố định, không theo reconstructed pose/intrinsics | `blender_engine.py` | World-space placement từ pose hoặc mô tả rõ chỉ là plate animation |
| BUG-014 | **P1** | Shot camera planner tạo `trajectory` nhưng safe renderer dựa preset `motion_2d`, geometry renderer tạo path khác từ keyframes; chỉnh camera chưa quyết định tất cả render | `camera_planner.py`, `renderer.py`, `render_worker.py` | Chuẩn hóa `CameraPathDocument` 1 nguồn chân lý, renderer adapter cùng tiêu thụ |
| BUG-015 | **P1** | Camera `safety_validation.passed = True` trong đường sinh preset; `confidence` cố định 0.85/0.92/0.95 không từ đo lường | `camera_planner.py` | Validate thật từ proxy/bounds/pose, nếu thiếu trả `UNKNOWN`, không pass giả |
| BUG-016 | **P1** | `moverse_applied=True` khi bật cấu hình nhưng chưa gọi endpoint/inference refine trajectory | `camera_planner.py`, `ai_adapter.py` | Chỉ set true kèm output có checksum và execution receipt |
| BUG-017 | **P1** | QC no-frame trả score mặc định 0.92/0.95/0.96, có thể được coi là pass | `ai_qc.py` | `INCONCLUSIVE/NOT_RUN`; không cho accept nếu thiếu frame hoặc không đồng bộ |
| BUG-018 | **P1** | GitHub Pages là single-file SPA dùng Canvas mock point cloud + `MediaRecorder`; tách rời backend/đường camera 3D thực | `index.html`, `apps/web`, `apps/api/app/ui.py` | Một Studio chính kết nối API; GitHub Pages chỉ là demo trung thực hoặc redirect |
| BUG-019 | **P1** | Phần ghi video Canvas chạy vòng `setTimeout(step, 10)` nhưng source 30 FPS, không quản lý realtime timestamps chuẩn | `index.html`, `startVideoExport` | Chỉ gọi server render hoặc local deterministic frame capture; ffprobe duration/fps gate |
| BUG-020 | **P1** | Ghép BGM giả định input video có `[0:a]`; source-image clips có thể không có audio stream | `renderer.py`, `concatenate_timeline` | Kiểm tra ffprobe; map BGM riêng cho video silent; amix khi có audio |
| BUG-021 | **P1** | `qc_video_output` chỉ kiểm tra tồn tại và >1024 bytes, không thật sự ffprobe/validate frames/codec/duration | `renderer.py` | ffprobe codec/duration/fps/dimensions, frame count, decode sample |
| BUG-022 | **P1** | File COLMAP/images có khả năng trùng basename; Blender script nội suy string từ `shot_name`; cần sanitize trước khi execute | `geometry_backend.py`, `blender_engine.py` | UUID/name mapping, JSON external data, no unsanitized script interpolation, test injection |
| BUG-023 | **P1** | Chưa có migration PostgreSQL chuẩn; SQLite schema bổ sung cột thủ công có nguy cơ không nhất quán | `apps/api/app/db/session.py` | Alembic, migrations, backfill, migration dry run/rollback |
| BUG-024 | **P1** | `get_capabilities` tuyên bố Wan available từ flags/VRAM/weights folder chứ không probe worker; logic ready >=12 GB trong khi field `min_vram_gb=16` | `capabilities.py` | Active handshake, model config check + probe job + thống nhất VRAM policy |
| BUG-025 | **P1** | Worker video timeline có thể dùng render completed cũ khi input/trajectory/config đổi | `render_worker.py`, `_process_timeline_render` | Artifact fingerprint gồm input hashes + config + engine/model versions, invalidation |
| BUG-026 | **P1** | Docker web build ngoài có thể hoạt động nhưng chưa có CI build+smoke tích hợp; `Dockerfile.gpu` chưa được chứng thực | `apps/web/Dockerfile`, `apps/api/Dockerfile.gpu` | matrix CI: Python, Next, Docker API, Docker web, GPU self-hosted |
| BUG-027 | **P2** | Phân loại road/bridge/culvert dựa heuristic tên file/màu, score 0.88 từ keyword không phải confidence được hiệu chuẩn | `image_analysis.py` | Calibrate, manual override, đánh dấu `heuristic`, tập ảnh thực |
| BUG-028 | **P2** | Tên/metadata chế độ có cả `2D_IMAGE_CAMERA`, `A/B/C` và `2.5d_lite`; dễ lệch UI/API/render | `camera_modes.py`, `camera_planner.py`, `schemas/contracts.py` | Versioned enums, compatibility mapping |
| BUG-029 | **P2** | Tài liệu báo phase, GPU và trạng thái đã xác minh mâu thuẫn | `README.md`, `PROJECT_STATUS.md`, `docs/*` | Truth registry, update docs từ CI evidence; giữ lịch sử |
| BUG-030 | **P2** | Chưa có bộ ảnh benchmark Civil3D/InfraWorks chuẩn được version hóa; unit mock không thay thế geometry test GPU | `tests/*`, `docs/BENCHMARK_DATASETS.md` | Dataset IDs, consent/license, golden outputs, artifacts và benchmark reports |

**Đánh giá triển khai:** phần lớn BUG-001..025 đã quan sát trực tiếp từ code; BUG-026..030 là lỗ hổng vận hành/tài liệu cần chứng minh bằng pipeline CI/benchmark. **Không khẳng định số test hiện ghi trong `PROJECT_STATUS.md` đã chạy trên baseline mới trong lượt audit này.**

---

## 3. Kiến trúc mục tiêu: 1 product, 1 API, 1 camera contract

~~~text
STUDIO UI (Next.js) ------- Auth/session ------> FastAPI BFF / REST
  | Upload/Review/Timeline                          |
  | Real 3D Preview (Three.js)                      +--> PostgreSQL (metadata/permissions)
  | Job Monitor / QC                                +--> Object Store (local/S3; immutable originals)
  |                                                +--> Outbox / Redis queue
  +-------------- WebSocket/SSE job events <---------+
                                                          |
                  +---------------------------------------+--------------------+
                  |                 |                     |                    |
            INGEST WORKER     RECON WORKER           RENDER WORKER        AI WORKER
             Pillow/OpenCV    COLMAP/quality         FFmpeg / Blender      Wan2.2/other
             grouping/QA      scene representation  Nerfstudio 3DGS       opt-in GPU
                  |                 |                     |                    |
                  +-----------------+---------------------+--------------------+
                                                          |
                                            FRAME/VIDEO QC / PROVENANCE
                                                          |
                                            Final compositor + ffprobe
                                                          |
                                          MP4 + manifest + source links
~~~

### 3.1. Chọn frontend thống nhất

- **Một ứng dụng authoritative:** `apps/web` Next.js với các màn hình dự án / asset / scene / Camera Studio / render / QC / export.
- Dùng TypeScript strict, API client generated từ OpenAPI, schema validation, error boundaries, loading/polling, no magic mock.
- Với 3D viewport dùng renderer thực (ví dụ Three.js + point cloud/mesh streaming). Chọn công cụ sau benchmark, không nhúng library chỉ để có canvas.
- `index.html` và `docs/index.html` chỉ giữ bản giới thiệu/tĩnh **không mô phỏng pass QC hoặc chạy AI thật**; sau migration, có thể thay bằng landing page redirect vào app có backend.
- `apps/api/app/ui.py` chuyển thành redirect compatibility hoặc deprecate qua 2 release.
- Không nhân đôi logic project/timeline giữa localStorage và DB. DB + API là nguồn dữ liệu dự án chuẩn; offline local drafts tách riêng, có nhãn.

### 3.2. Chọn backend và worker

- FastAPI chỉ validate/auth/ghi DB/queue/stream trạng thái, không render GPU/FFmpeg dài trong HTTP request.
- PostgreSQL chuẩn production; SQLite chỉ cho local/dev/test. Dùng Alembic schema migrations.
- Redis hoặc DB queue durable; atomic job claim, attempts, lease, heartbeat, retry/backoff, cancellation, worker resource quotas.
- Worker GPU riêng, environment khóa phiên bản CUDA/PyTorch/Nerfstudio; không bắt buộc cài trên máy dùng CPU.
- Adapter interfaces có typed contracts: `ImageAnalyzer`, `Reconstructor`, `SceneRepository`, `CameraPlanner`, `RenderBackend`, `AIProvider`, `QualityEvaluator`, `Composer`, `ArtifactStore`.
- Dùng event/log có `job_id`, `project_id`, `scene_id`, `engine_version`, `input_hashes`, `artifact_sha256`.

### 3.3. Một camera schema, nhiều backend

`CameraPathDocument` canonical: schema_version, scene_id, coordinate_frame, scale_status, FOV/intrinsics, keyframes {timestamp, pos, quat, focus, source image}, interpolation, constraints, validation status, revision, hash.

**Invariant quan trọng:** Camera Studio preview, Blender, Nerfstudio, 2D motion renderer và timeline **phải đọc cùng revision** của CameraPathDocument; không tạo camera mới ngầm trong render worker.

- Với mode A: pose nối với reconstructed camera/world transform; validate chống xuyên geometry/out-of-bounds/low coverage.
- Với mode B: path là symbolic 2.5D/transition từ ảnh theo thứ tự, không cho UI quảng cáo flythrough 3D.
- Với mode C: frame transform x/y/scale có constraint crop/edge exposure.
- `confidence` và `safety_status` phải từ phép đo; thiếu dữ liệu là `UNKNOWN`; không fixed 0.95, không fixed pass true.
- Camera preview phải có overlay coverage/confidence và badge render mode **thực**, không chỉ label giả.

### 3.4. Scene quality gate

- `READY_3D`: số ảnh đăng ký, ratio, reprojection error, baseline/angle coverage, depth/point density, vùng camera an toàn đều qua threshold đã hiệu chuẩn.
- `DEGRADED_3D`: có scene nhưng chỉ render vùng nhỏ/shot giới hạn, được người dùng đồng ý.
- `FALLBACK_2D`: ảnh ít, trùng góc, motion blur, thiếu texture, sai scale, reconstruction thất bại.
- Không dùng threshold cố định như chứng nhận thiết kế. Ghi sample size và lý do cho mọi decision.

---

## 4. Cấu trúc repo đích (refactor có migration)

~~~text
AI-Video-/
├── README.md                       # product + quickstart ngắn, có kết quả verified
├── MASTER_REFACTOR_PLAN.md          # tài liệu chuẩn, phase gates
├── SKILL.md                         # chỉ dẫn agent trỏ về canonical plan
├── PROJECT_STATUS.md                # nhật ký trạng thái + evidence
├── LICENSE / NOTICE / THIRD_PARTY_LICENSES.md
├── .github/
│   ├── workflows/{ci,security,docker,gpu-nightly}.yml
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── apps/
│   ├── web/                         # Next.js Studio duy nhất
│   │   ├── app/{projects,studio,jobs,settings}/
│   │   ├── src/{features,components,lib,generated-api}/
│   │   └── tests/
│   └── api/                         # FastAPI + Alembic
│       ├── app/
│       │   ├── api/v1/
│       │   ├── auth/
│       │   ├── core/
│       │   ├── db/
│       │   ├── domain/
│       │   ├── schemas/
│       │   ├── services/
│       │   └── workers/
│       ├── migrations/
│       └── tests/
├── packages/
│   ├── contracts/                   # canonical typed/json schema
│   ├── camera/                      # math, trajectory, validation
│   ├── ingest/                      # QA, grouping, overlap
│   ├── reconstruction/              # colmap, scene export
│   ├── render/                      # FFmpeg/Blender/Nerfstudio adapters
│   ├── ai/                          # provider interfaces, QC
│   └── storage/                     # local/S3 compatible interface
├── workers/
│   ├── ingest-worker/
│   ├── geometry-worker/
│   ├── render-worker/
│   └── ai-worker/
├── infra/
│   ├── docker/
│   ├── compose/{dev,cpu,gpu}.yaml
│   └── deploy/
├── configs/
│   ├── camera_presets/
│   ├── render_profiles/
│   └── quality_profiles/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   └── golden/
├── benchmarks/
│   ├── manifests/                   # không commit dữ liệu nhạy cảm/GB
│   ├── scripts/
│   └── reports/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── OPERATIONS.md
│   ├── RUNBOOK.md
│   ├── LICENSES.md
│   ├── ADR/
│   └── legacy/                      # chỉ sau khi audit/migrate
└── tools/{dev,release,migrations}/
~~~

**Không chuyển toàn bộ thư mục đồng loạt.** Tiến hành strangler migration: giữ compatibility import/endpoints, chuyển dần từng module, chạy test và canary mới xóa phiên bản cũ. Không đưa binary weights hay input images của khách hàng vào Git.

---

## 5. Contract dữ liệu, công việc và API mới

### 5.1. Bảng production tối thiểu

`users`, `organizations` (optional phase), `memberships`, `projects`, `assets`, `asset_versions`, `scenes`, `reconstructions`, `shots`, `camera_paths`, `render_jobs`, `ai_jobs`, `qc_reviews`, `artifacts`, `events`.

Các trường quan trọng:

- `owner_id`/`tenant_id` cho mọi entity thuộc khách hàng; FK/index rõ ràng.
- `hash/version` của input, preset, model, code, camera path, QC profile; event audit không mất.
- `job.state`: queued / claimed / running / cancelling / cancelled / retry_wait / failed / completed.
- `pipeline.stage`: ingest / analyze / reconstruct / plan / render / enhance / evaluate / compose / export.
- `artifact.kind`: original_image / sparse_model / camera_path / frame_sequence / render_raw / render_ai / report / final_mp4.
- `artifact.provenance`: created_by_engine, execution_backend, shader/model revision, input artifact IDs.
- `ai_verification`: `NOT_RUN` / `PRODUCED` / `QC_PASSED` / `QC_FAILED` / `USER_ACCEPTED` / `USER_REJECTED`.

### 5.2. Các endpoint mục tiêu

- `POST /api/v1/projects`, `GET /api/v1/projects`, `GET /api/v1/projects/{id}`.
- `POST /api/v1/projects/{id}/assets` (stream, MIME validation, signed URL tùy storage), `POST .../analyze`.
- `POST /api/v1/projects/{id}/scenes`, `POST /api/v1/scenes/{id}/reconstructions`, `GET /api/v1/scenes/{id}/quality`.
- `POST /api/v1/shots`, `PUT /api/v1/shots/{id}/camera-path` (optimistic revision), `POST .../camera-path/validate`.
- `POST /api/v1/render-jobs`, `GET /api/v1/jobs/{id}`, `POST .../cancel`, `POST .../retry`.
- `POST /api/v1/ai-jobs`; thiếu model/provider → `409/422 unavailable`, không `completed`.
- `GET /api/v1/jobs/{id}/events` (SSE/WebSocket), `GET /api/v1/artifacts/{id}/download` (scoped auth).
- `POST /api/v1/projects/{id}/exports`; `GET /api/v1/projects/{id}/manifest`.
- Viết OpenAPI versioned + examples, response errors chuẩn (code, message, action, correlation_id); route cũ deprecate có mapping trong ít nhất một release.

### 5.3. Idempotency, cache, retries

- `job_key = hash(tenant, project, asset_hashes, camera_revision, renderer, config, versions, output_profile)`.
- DB unique partial constraint phù hợp khi `queued/running/completed` và không force-rebuild; trả job hiện hữu.
- Atomic claim qua `SELECT ... FOR UPDATE SKIP LOCKED` trên Postgres hoặc Redis lock+DB lease; không dùng SELECT rồi set status riêng lẻ.
- Heartbeat, expiration, reclaim stale jobs; max attempts + exponential backoff, phân biệt transient/permanent error.
- `cancel_requested` kiểm tra trong long-running process; kill process group an toàn; cleanup temp; không xóa original.
- Artifact được ghi vào temp file, ffprobe/sha256 xong mới atomic publish; không dùng file partial làm kết quả.
- Có quota CPU/RAM/VRAM/disk, giới hạn đồng thời theo GPU và user.

---

## 6. Phases chính thức — 12 cổng nghiệm thu, làm theo thứ tự

**Quy ước:** mỗi phase phải có issue/PR, checklist, kết quả test và evidence trong `PROJECT_STATUS.md`. Chưa đạt gate thì **không chuyển phase**. Các phase có thể chuẩn bị song song nhưng không được tuyên bố hợp nhất thành công khi thiếu dependency.

### PHASE 00 — Freeze, backup, baseline, ownership

**Mục tiêu:** biết chính xác code cũ đang chạy được đến đâu, có rollback.

- [ ] P00-01 Tạo tag `pre-refactor-20261013` trên commit baseline sau khi kiểm tra không trùng tag; ghi SHA.
- [ ] P00-02 Backup database mẫu và storage mẫu (ẩn thông tin cá nhân), kiểm tra restore.
- [ ] P00-03 Chụp tree/checksum source, ghi inventory endpoint, UI, tests, worker, dependency.
- [ ] P00-04 Chạy `pytest`, `npm run build`, Docker builds trên môi trường sạch; lưu log và version.
- [ ] P00-05 Tạo bug issue BUG-001..030 và risk register. Ghi rõ `not_run` nếu không đủ môi trường.
- [ ] P00-06 Lập board: task ID, owner, branch, PR, dependency, artifact, gate, status.

**Gate G00:** có baseline SHA, backup restore verified, bản ghi command/test output và issue board. **Không tuyên bố code sạch trước khi chạy.**

### PHASE 01 — Truthfulness + P0 security gates

**Mục tiêu:** không trả kết quả giả, không mở API nguy hiểm.

- [ ] P01-01 Xóa QC random ở Pages; chưa có QC thật ⇒ hiển thị `NOT_RUN`, không có “đạt chuẩn”.
- [ ] P01-02 Sửa API AI job: không source ⇒ fail 422; không worker ⇒ unavailable; copy-only ⇒ `NOT_AI`.
- [ ] P01-03 QC dùng original render và enhanced render khác nhau; chiết/align frame theo timestamp; fail-closed.
- [ ] P01-04 Bảo vệ auth + project ownership; deny truy cập cross-project/tenant; session/cookie/CORS/CSRF tùy deployment.
- [ ] P01-05 Upload giới hạn bytes trong vòng lặp, kiểm tra magic/decode/pixel, tên lưu UUID, quota, chống decompression bomb.
- [ ] P01-06 Log secret redaction, masked error; loại bỏ raw internal path/traceback tại API public.
- [ ] P01-07 Tạm tắt UI/buttons không được backend hỗ trợ; ghi lý do/capabilities.

**Gate G01:** các test bắt buộc PASS: QC no input returns NOT_RUN; original=AI reference test chỉ cho demo check chứ không gắn AI thật; fake-success không còn; anonymous/cross-tenant 401/403; oversize 413; corrupted image 4xx. Không dùng mock để chứng nhận security production.

### PHASE 02 — Reproducible build, packaging, CI

**Mục tiêu:** clone sạch chạy được trên máy CPU, bật GPU khi môi trường hỗ trợ.

- [ ] P02-01 Sửa `apps/api/Dockerfile` để COPY/install đúng `packages` và dependency package; kiểm tra startup FastAPI, imports.
- [ ] P02-02 Viết lại `Dockerfile.gpu` thành single base, lock CUDA/PyTorch/gsplat/Nerfstudio, bỏ FROM/install lặp, path COPY sai.
- [ ] P02-03 Compose profiles `cpu/dev/gpu`; health/readiness/liveness; một entrypoint worker thống nhất.
- [ ] P02-04 Tạo lockfiles Python/web; SBOM, vulnerability scan, image pin bằng digest nơi cần.
- [ ] P02-05 GitHub Actions: format/lint/typecheck/unit/contract/build/docker smoke, artifacts, no secrets.
- [ ] P02-06 GPU smoke trên self-hosted runner khi có; không đánh dấu pass nếu runner thiếu GPU.
- [ ] P02-07 Sửa quickstart Windows/Linux; self-check script báo FFmpeg/COLMAP/Blender/Nerfstudio/weights.

**Gate G02:** máy sạch `docker compose up --build` với CPU profile → API health + web + worker + video ngắn; build GPU chạy capability probe trên runner GPU; docs đúng command. Nếu GPU chưa có, gate GPU ghi `BLOCKED_HARDWARE` và không công bố 3D ready.

### PHASE 03 — Domain, persistence, job orchestration

**Mục tiêu:** dữ liệu/hàng đợi đúng, không render trùng, có resume.

- [ ] P03-01 Thiết kế contracts versioned; OpenAPI client gen TypeScript.
- [ ] P03-02 Alembic migrations + backfill SQLite→Postgres, FK/index/tenant filters.
- [ ] P03-03 Unified state machine strict; illegal transition throws, CAS + event log.
- [ ] P03-04 Claim atomic, leases, retry, cancellation, timeout, idempotent job creation.
- [ ] P03-05 Artifact store và immutable originals + project manifest.
- [ ] P03-06 Cache/recompute theo content hash, invalidation khi camera/config đổi.
- [ ] P03-07 Đưa `run-now` sau dev feature flag; production không render đồng bộ trong request.
- [ ] P03-08 Chi tiết logs/metrics/traces: latency, queue wait, GPU, storage.

**Gate G03:** 2–4 worker cùng claim chỉ 1 execution hiệu lực; retry sau crash không corrupt; cancel giải phóng process; DB migration up/down; file partial không bị tải làm MP4.

### PHASE 04 — Ingestion, scene grouping, evidence-based analysis

**Mục tiêu:** từ hàng trăm ảnh thành nhóm cảnh có nguồn gốc rõ.

- [ ] P04-01 Upload streaming/chunk/resumable optional, EXIF transform, checksums, previews.
- [ ] P04-02 Phát hiện duplicate exact/perceptual; ORB/SIFT overlap + graph connectivity, không bắt buộc CPU khủng.
- [ ] P04-03 Classification heuristic có nhãn `estimated_by_heuristic`, confusion-matrix, override và audit.
- [ ] P04-04 Lý trình/nút giao/cầu/cống: user metadata/CSV sidecar tùy chọn (không yêu cầu model CAD).
- [ ] P04-05 Auto select A/B/C theo overlap/reconstructability; user override nhưng cảnh báo.
- [ ] P04-06 Bảo toàn order, scene groups, shot source IDs; UI không tự suy định tọa độ thực.

**Gate G04:** bộ 5–6 dataset (ảnh tốt, rời rạc, trùng, mờ, 1 ảnh, không overlap), tất cả kết quả grouping/QA reproducible; không gắn “camera 3D available” khi chỉ có ảnh rời rạc.

### PHASE 05 — CPU renderer / timeline / video QC ổn định

**Mục tiêu:** có sản phẩm dùng được ngay khi không có GPU.

- [ ] P05-01 Một CPU renderer đọc keyframes 2D từ canonical path, không dùng preset không đồng bộ.
- [ ] P05-02 FFmpeg deterministic FPS/resolution/duration, transitions theo timestamps, xử lý VFR/audio cases.
- [ ] P05-03 BGM, narration, intro/outro, text, overlay fonts VN Unicode bằng font licensed; ffprobe audio stream trước amix.
- [ ] P05-04 Media QC: ffprobe codec/profile/fps/duration/size, decode sample frames, black frames, truncated file.
- [ ] P05-05 Export manifests với `effective_mode=2d_source_motion`, cache key, reproducibility.
- [ ] P05-06 Giới hạn RAM: stream frames / FFmpeg filters, không tích toàn bộ 4K frames.

**Gate G05:** 1 ảnh→MP4 5 s và 10 ảnh→timeline 30 s có số frame, duration/fps đúng theo tolerance; MP4 phát được; BGM hoạt động khi video gốc không audio; cancel/retry hoạt động.

### PHASE 06 — CameraPathDocument v2 & camera safety

**Mục tiêu:** renderer nào cũng đọc một quỹ đạo cùng revision.

- [ ] P06-01 Gộp `camera_math`, `camera_planner`, `geometry/camera_path` thành contracts v2 (adapter compatibility v1).
- [ ] P06-02 Quaternion convention (wxyz vs xyzw), coordinate frames (COLMAP/OpenCV, Blender/OpenGL, Nerfstudio) và intrinsics có unit test golden.
- [ ] P06-03 Preset 10 kiểu; thay offset mặc định bằng scene-aware constraints khi có geometry; không giả AI path.
- [ ] P06-04 PathValidator thật: smoothness, angular velocity, coverage bounds, collision proxy, camera clipping, unknown-data state.
- [ ] P06-05 Revision/hash, optimistic editing, undo, path validation API; Blender và Nerfstudio dùng cùng path.
- [ ] P06-06 Tạo camera storyboard theo tuyến từ grouping/ảnh được đăng ký; route station khi metadata có sẵn.

**Gate G06:** sửa camera keyframe thay đổi frame được render từ backend tương ứng; test transform cross-engine + roundtrip; invalid geometry rejected/fallback; không còn hardcode `safety_validation.passed=True`.

### PHASE 07 — 3D feasibility & COLMAP/Nerfstudio/Blender live

**Mục tiêu:** proof-of-video 3D thực, không chỉ script.

- [ ] P07-01 Tạo dataset nhiều ảnh InfraWorks của **cùng một cảnh**: ≥15 ảnh (khuyến nghị 20–50) đủ baseline/chồng phủ; metadata/quyền sử dụng rõ.
- [ ] P07-02 Chạy COLMAP feature, match, mapper, model statistics; mapping registered poses/camera IDs đúng với ảnh nguồn.
- [ ] P07-03 Xuất sparse model/point cloud, preview viewer thật; không vẽ point cloud giả trên Canvas.
- [ ] P07-04 Quality gate theo error/coverage/density, vùng camera được phép. Không “READY_3D” bằng flag dependency đơn thuần.
- [ ] P07-05 Chạy Nerfstudio `splatfacto` bằng script/version pinned; lưu logs, checkpoint, training metrics, reproducible path.
- [ ] P07-06 Sửa Blender adapter: gọi headless thật khi requested, metadata image planes từ pose hoặc nêu rõ plate layout fallback.
- [ ] P07-07 Render ≥5 s camera bay có dịch chuyển thị sai (parallax) thật, kiểm tra không xuyên scene và điểm mù.
- [ ] P07-08 Loại bỏ double-training khi scene đã có checkpoint; render reusable artifacts.
- [ ] P07-09 Benchmark máy GPU (VRAM, RAM, FPS, throughput, crash/OOM), cấu hình 16/24 GB tùy model.
- [ ] P07-10 Failure handling: reconstruction không đạt → B/C kèm chi tiết, không tạo geometry giả.

**Gate G07:** có video MP4 novel-view 3D thật + artifact pose/scene/checkpoint + ít nhất 1 accepted trajectory + log CUDA/driver/tool versions + screenshot viewer 3D lấy từ scene; kiểm thử cả dataset failover. **Gate này không thể được đóng chỉ với unit tests.**

### PHASE 08 — Unified Studio (6 màn hình) và preview đúng trạng thái

**Mục tiêu:** UX giống quy trình công cụ dựng hình chuyên nghiệp nhưng trung thực.

- [ ] P08-01 Migrated app chính Next.js: Dashboard / Assets / Reconstruction / Camera Studio / Render & AI / Export.
- [ ] P08-02 Chuyển các thiết kế có giá trị từ legacy `index.html`, không copy logic giả vào app mới.
- [ ] P08-03 Camera viewport Three.js hiển thị point cloud/mesh/frustums/keyframes thật từ artifacts; fallback 2D được gắn nhãn.
- [ ] P08-04 Multi-track timeline thật: shots, audio, captions, transitions, keyframes, selection, drag, undo/redo.
- [ ] P08-05 API event progress, failure, retry, cancel; preview low-res, render full; show backend, VRAM, quality.
- [ ] P08-06 QC compare side-by-side video thực, reject/revert, không random.
- [ ] P08-07 Đồng bộ drafts/localStorage với project DB bằng explicit save, tránh mất dữ liệu.
- [ ] P08-08 Legacy Pages: redirect/landing/demo read-only có nhãn DEMO; cấm gắn nhãn output 3D/AI nếu chỉ Canvas.

**Gate G08:** automated Playwright E2E: upload → analyze → create scenes/shot → move camera → preview → render → download; không có UI control inert. So sánh trajectory trên UI và artifact JSON cùng revision.

### PHASE 09 — Optional AI inference thật + QC pháp lý/kỹ thuật

**Mục tiêu:** AI video cinematic có thể sử dụng, không đánh tráo geometry.

- [ ] P09-01 Chọn provider license-compatible theo từng model/weights. Đọc terms/redistribution cụ thể tại thời điểm tích hợp; chưa xác minh ⇒ BLOCK.
- [ ] P09-02 Wan2.2 inference worker thật hoặc ComfyUI workflow thực, output frames/video + seed/model/checkpoint revision, timeout/cancel/OOM.
- [ ] P09-03 MoVerse/other novel view là experimental worker riêng. Chỉ đánh dấu active khi request→inference→artifact chứng minh; nếu không đạt thì loại khỏi release.
- [ ] P09-04 DUSt3R research-only/non-commercial nếu giấy phép không cho sản phẩm thương mại; không bundle default.
- [ ] P09-05 Không dùng `copy2` + metadata diffusion. Nếu user chọn color-grade, ghi `COLOR_GRADED_NOT_GENERATIVE`.
- [ ] P09-06 Trích đồng bộ frame từ original vs AI output; so edge/landmark/temporal stability và review ảnh cầu, cống, biển báo, số làn. Lưu QC artifact.
- [ ] P09-07 QC thiếu dữ liệu ⇒ INCONCLUSIVE, AI không được dùng mặc định trong final render. Người dùng có quyền từ chối.
- [ ] P09-08 VRAM policy phụ thuộc model/resolution/precision/quantization thực, probe worker + dry-run; UI dự báo tài nguyên, cảnh báo chi phí.
- [ ] P09-09 Golden scenes safety: không thay số làn, không đổi barrier/vạch sơn, không thay hình học nhịp cầu; manual approval.

**Gate G09:** một video AI **khác thật về nội dung** so với đầu vào, có logs inference, seed, model SHA/checkpoint, QC so 2 file, ảnh trước/sau và user approval; pipeline gốc vẫn chạy nếu AI worker offline.

### PHASE 10 — Test matrix, benchmark, reliability

**Mục tiêu:** có bằng chứng sản phẩm chạy ổn trong thực tế.

- [ ] P10-01 Unit > core modules, contract schema, path math, coordinate transforms.
- [ ] P10-02 Integration: SQLite local, PostgreSQL/Redis, FFmpeg, Blender headless, COLMAP/Nerfstudio GPU when available.
- [ ] P10-03 E2E với datasets Civil3D/InfraWorks **đã có quyền sử dụng**, tất cả mode A/B/C.
- [ ] P10-04 Stress/failure: corrupt files, max upload, duplicate, lost worker, slow GPU, disk full, cancel, retry, concurrent jobs, shutdown.
- [ ] P10-05 Security SAST/SCA, auth/IDOR, MIME spoof, zip bomb, path traversal, prompt/filename/script injection, malicious metadata.
- [ ] P10-06 Benchmark quality & performance lưu nguồn, revision, OS, GPU, duration; không dùng mục tiêu số cứng chưa hiệu chuẩn để tự phong pass.
- [ ] P10-07 Accessibility/i18n VN/EN, test responsive keyboard, TTS/fonts Unicode.
- [ ] P10-08 CI evidence links tới từng acceptance scenario.

**Gate G10:** all critical/major bugs đóng có test; **zero unexplained fake pass**; CPU E2E bắt buộc; GPU E2E chạy trên runner GPU được ghi log; không được thay thế kết quả GPU bằng mock.

### PHASE 11 — Production release, observability, operations

**Mục tiêu:** phát hành nhiều người dùng mà không mất dữ liệu.

- [ ] P11-01 Auth, RBAC, tenant isolation, private object storage, signed downloads, quotas/rate limits.
- [ ] P11-02 DB backups + restore drills; storage retention/lifecycle, cleanup, encrypted transport, audit logs.
- [ ] P11-03 Observability: Prometheus/OpenTelemetry/Sentry tương đương tùy stack, logs, alert cho worker, GPU OOM, job stuck, disk low.
- [ ] P11-04 Versioned migration, canary, feature flags, blue/green hoặc safe rollback.
- [ ] P11-05 Terms/privacy/license/SBOM; đảm bảo quyền upload ảnh bản vẽ thiết kế.
- [ ] P11-06 GPU deployment optional, CPU-only base tier, max concurrency/quota controls.
- [ ] P11-07 Runbook incident + operator dashboard, support diagnostics file, changelog.
- [ ] P11-08 Tag stable release sau khi đủ artifacts, không dùng tag `2.0.0 complete` chỉ vì commit message nói vậy.

**Gate G11:** staging release chạy đầy đủ flows, restore backup, test quyền đa người dùng, negative auth, load test, rollout/canary và quy trình rollback được diễn tập.

---

## 7. Thứ tự ưu tiên phụ thuộc & release checkpoints

| Checkpoint | Phase phải qua | Sản phẩm có thể công bố |
|---|---|---|
| **MVP-CPU** | G00–G05 | Nhập ảnh → timeline → video MP4 2D an toàn, có bảo mật cơ bản, không quảng cáo camera 3D |
| **CAMERA-BETA** | G06 | Camera path versioned/chỉnh sửa được, ảnh hưởng đến output, kiểm tra dữ liệu |
| **3D-ALPHA** | G07 | Tái dựng+bay camera 3D thật trên bộ ảnh phù hợp, có benchmark GPU |
| **STUDIO-BETA** | G08 | Một giao diện web thống nhất, không demo fake |
| **AI-OPT-IN** | G09 | AI inference và QC thật, người dùng phê duyệt |
| **PUBLIC-RELEASE** | G10–G11 | Sẵn sàng triển khai đa người dùng |

**Luồng critical path:** G00 → G01/G02 → G03 → G04 → G05 → G06 → G07 → G08 → G09 → G10 → G11. Có thể chuẩn bị giao diện và AI adapter song song nhưng không gắn trạng thái verified khi gates phụ thuộc chưa qua.

**Ràng buộc công việc:** ưu tiên BUG-001..011, BUG-021, sau đó BUG-012..020, BUG-022..030. Agent chọn các task trong phase thay vì chạy tất cả một lần.

---

## 8. Bộ dữ liệu nghiệm thu và KPI

| Dataset | Nội dung | Kết quả mong đợi |
|---|---|---|
| D01-single | 1 ảnh phối cảnh cầu | Mode C, MP4, không gắn nhãn 3D |
| D02-sequence | 8 ảnh cùng tuyến có thứ tự rõ | Mode B, chuyển cảnh mượt, timeline theo ảnh |
| D03-overlap | 20–50 ảnh cùng nút giao với baseline tốt | Thử Mode A; nếu reconstruction pass thì novel-view 3D; nếu fail thì log nguyên nhân |
| D04-disconnected | 12 ảnh nhiều nơi không chồng phủ | Tách groups hoặc fallback B/C, không forced single scene |
| D05-drawings | Bình đồ/trắc dọc/trắc ngang Civil 3D | 2D presentation, đọc metadata đúng; không ép SfM |
| D06-structure | Cầu/cống/vạch sơn được nhìn từ nhiều góc | Kiểm tra hình học frame-to-frame và human review |
| D07-fail | File hỏng, trùng, quá lớn, không đủ quyền | Predictable error, không leak/không corrupt |
| D08-stress | Nhiều project/job cùng lúc | Queue no double execution, quotas/retry/cancel |

### 8.1. KPI bắt buộc đo thực

- **Rendering:** video mở được; H.264/MP4, FPS/resolution/duration kiểm bằng ffprobe, audio đúng.
- **Scene reconstruction:** registered ratio, reprojection error, coverage, baseline, point density, reprojection validation; lưu cả kết quả không đạt.
- **Camera:** max angular speed, jerk, scene coverage, collision proxy; đo theo scale calibrated/relative rõ ràng.
- **AI:** output provenance, temporal stability, edge/structure differences, lỗi do AI, user approval; không mặc định AI luôn an toàn nếu score cao.
- **System:** job success rate, median/P95 time, worker crashes, OOM, disk usage, concurrent fairness, retry rate.
- **Trust:** tỷ lệ giả trạng thái “success” = **0**, báo cáo missing metrics là NOT_RUN chứ không pass.

**Ngưỡng gợi ý ban đầu cần calibration:** FPS 24/30, preview 720p, final 1080p; duration error ≤1 frame ở đầu-cuối khi pipeline không dùng AI VFR; no missing frames; job idempotency khi double-click. Các quality threshold Edge IoU/SSIM chỉ được sử dụng sau khi có human-labeled benchmark cho bản vẽ hạ tầng; không dùng ngưỡng tự chọn làm “đúng thiết kế”.

### 8.2. Hồ sơ bằng chứng một scenario

Mỗi run lưu: dataset_id/hash; commit SHA; platform/OS/driver/GPU/VRAM; model/weights/license; runtime flags; input count; registered images; selected mode; render engine effective; camera path hash; output MP4 path+sha; ffprobe JSON; quality report; screenshots thật; failing logs; approved reviewer; timestamp.

---

## 9. Bảo mật và chất lượng production — các gate phi chức năng

- **AuthN/AuthZ:** tất cả endpoints/scoped artifacts check owner; không phụ thuộc UI giấu nút. Test cố tình đọc project khác bằng ID.
- **Upload:** MIME sniffing, verify pixel size/EXIF, byte caps in streaming, file locks/temp atomic, antivirus hoặc sandbox khi public; chống ảnh nén độc hại.
- **Command execution:** mọi subprocess dùng argv list, timeout, kill group; không shell=True với user input; stdout/stderr được redact; script Blender không interpolate raw user strings.
- **Storage:** UUID content paths, immutable originals, signed URLs, ownership metadata, lifecycle/quota, versioned deletion.
- **Secrets:** env/secret manager, không commit tokens, không log raw Bearer, CORS allowlist. Test GitHub secrets leak.
- **Multitenancy:** row-level filters/test tenant IDs cho mọi query; unique project/shot/asset relationships.
- **Reliability:** migrations transaction/backup; object store consistency; queue durability; jobs resumable; log trail.
- **Third-party licenses:** kiểm tra cụ thể code/checkpoints/weights/FFmpeg binary dependencies theo phiên bản; DUSt3R NC không bundle cho thương mại; hợp đồng GPU/cloud không mặc định miễn phí.
- **Privacy:** bản vẽ hạ tầng có thể là tài liệu nội bộ; không gửi provider AI bên thứ ba khi user chưa opt-in và chưa rõ chính sách dữ liệu.

---

## 10. Chính sách chuyển đổi, dọn repo, rollback

### 10.1. Migration thay đổi code

1. Freeze baseline/tag và backup DB/storage.
2. Refactor bằng PR nhỏ theo phase, không giant-PR gồm UI+DB+GPU+AI.
3. Khi thay API/schema, tạo compatibility adapter + migrate data + test old/new song song.
4. Đưa feature mới sau flag; default OFF đối với AI, 3D experimental, new UI cho đến khi gate pass.
5. Chạy regression với dataset golden; nếu fail/UX mất dữ liệu, revert flag hoặc rollback PR.
6. Chỉ xóa duplicate code/index sau khi đã chứng minh parity và người dùng không phụ thuộc endpoint cũ.
7. Ghi breaking changes/migration guide/changelog trước mỗi release.

### 10.2. Dọn tài liệu

- **Giữ:** `MASTER_REFACTOR_PLAN.md` canonical, `README.md`, `PROJECT_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/LICENSES.md`.
- **Tham khảo lịch sử:** `SKILL_CANONICAL.md`, `docs/skills/*`, `docs/ARCHITECTURE_AUDIT_AND_PLAN.md`; mark legacy và di chuyển `docs/legacy/` trong phase refactor docs, chỉ sau khi review.
- **Pages:** giữ `index.html` tạm thời để tránh gãy link; đổi tên/bỏ bản `docs/index.html` khi deployment mới đã xác minh.
- Không commit bin camera render/weights vào git; artifact release ở object storage hoặc GitHub Releases phù hợp.

### 10.3. Khôi phục khi phase thất bại

- Frontend: feature flag sang bản cũ, rollback deployment.
- Worker: drain queue, stop new job claims, giữ original input và job provenance; resubmit version cũ.
- DB: restore từ backup hoặc downgrade theo migration đã kiểm thử; không auto-drop tables.
- Artifacts: versioned keys, không ghi đè video verified; publish atomic.
- Git: revert commit/PR, **không force-push**.

---

## 11. Template nhiệm vụ cho coding agent — áp dụng nguyên văn

### 11.1. Quy tắc thực thi

**Vai trò:** Principal Engineer / Computer Vision / Rendering / Security / QA.

**Repository:** `hieudang99dd/AI-Video-`. Bạn được phép sửa toàn bộ code, kiến trúc, quy trình và thư mục nhằm đạt gates của tài liệu này. **Không tự ý xóa dữ liệu hay xác nhận nghiệm thu mà không có bằng chứng.**

**Nhiệm vụ trên mỗi lần chạy:**

1. Đọc `MASTER_REFACTOR_PLAN.md`, `SKILL.md`, `PROJECT_STATUS.md`, `README.md`, git status/branch/head; không dựa vào bộ nhớ lời hứa cũ.
2. Xác định phase gate đầu tiên chưa qua và issue chưa đóng theo priority.
3. Tạo branch `refactor/pXX-<short-task>`; không ghi đè thay đổi chưa commit của người dùng.
4. Viết test tái hiện lỗi hoặc acceptance test trước khi sửa.
5. Sửa code thực, cập nhật types/contracts/migrations/docs tương ứng; không chỉ thay text/UI/mock.
6. Chạy lint, format, typecheck, unit, integration, builds, và GPU tests nếu có phần cứng; attach output logs. Không đủ tool thì báo `NOT_RUN`.
7. Trong PR trình bày: change summary, files, bug IDs, tested commands/results, artifacts, before/after, migration risk, rollback, known blockers.
8. Review và merge có kiểm soát; cập nhật `PROJECT_STATUS.md` bằng evidence link; tuyệt đối không nâng status trên lời khẳng định của agent.
9. Chỉ chuyển phase sau gate check. Không tiếp tục thêm feature trước khi sửa P0.
10. Nếu có phần chưa hoàn thành, ghi `BLOCKED`, vẫn hoàn thiện phần độc lập; không tạo fake success.

### 11.2. Prompt kickoff ngắn, không phải nhập lại spec dài

> Đọc toàn bộ `MASTER_REFACTOR_PLAN.md` và source repo tại HEAD. Thực hiện **Phase chưa qua gate đầu tiên**. Trước khi sửa, viết bảng các task ID, bằng chứng lỗi, file sửa, test và dependency; sau đó triển khai mã nguồn thực và chạy test. Được quyền cấu trúc lại toàn bộ repo nhưng phải giữ backup, API migration và rollback. Không dùng mock/fake để tuyên bố geometry/AI/QC hoạt động. Cuối cùng ghi PR/report và cập nhật `PROJECT_STATUS.md` với trạng thái có bằng chứng.

### 11.3. Checklist PR

- [ ] Có BUG/PXX ID và link phase
- [ ] Có minimal reproducer/golden dataset
- [ ] API/schema changes + migration
- [ ] Bảo mật/auth/ownership/validation
- [ ] Logs/artifact provenance/cancel/retry
- [ ] Unit/contract/integration/e2e status đính kèm
- [ ] Câu nào trong UI tuyên bố `ready/verified/AI_ENHANCED` có artifact thật
- [ ] CPU fallback vẫn chạy
- [ ] Updated docs + runbook + rollback
- [ ] No new secret/model weights in git
- [ ] Trạng thái phase/capability không bị tô hồng

---

## 12. Nghiệm thu “hoàn thiện repo” — Definition of Done cấp sản phẩm

Repo **chỉ được gọi “thực chiến”** khi tất cả điểm sau được kiểm chứng:

1. Fresh install CPU chạy từ docs và tạo MP4 được ngay, không yêu cầu API key trả phí.
2. Các trường hợp A/B/C có phân loại và giải thích giới hạn đúng; mode A đã chạy bộ ảnh thật trên GPU với evidence.
3. Một camera path chỉnh sửa trên UI ra đúng video ở renderer tương ứng; không có path giả song song.
4. Không có QC random, copy-file-as-inference, safety fixed-pass, simulator-as-live, file tồn tại nhưng gắn “validated MP4”.
5. AI inference optional thật, QC thật và human approval; tắt AI vẫn render đầy đủ.
6. Không có leak cross-user, path traversal/oversized upload, job execution duplicate, partial artifact.
7. CI CPU + GPU validation pipeline chạy với dữ liệu golden và môi trường thật; có release artifacts/logs.
8. Khôi phục database/artifacts và rollback release đã được diễn tập.
9. Một Studio authoritative, UX đầy đủ; GitHub Pages không quảng cáo tính năng backend giả.
10. License, privacy, model checkpoint/hardware matrix được kiểm tra ở version release cụ thể.

---

## 13. Trạng thái baseline (không phải lời hứa)

| Khả năng | Mức baseline từ source | Được gọi “hoàn tất” chưa? |
|---|---|---|
| FastAPI / DB / shot / worker abstractions | Code có thật | **Chưa** production-secure |
| CPU 2D FFmpeg render | Code có thật, có tests viết sẵn | Cần chạy lại clean E2E |
| Camera math + presets | Code có thật | Chưa thống nhất với renderer |
| COLMAP + Nerfstudio integration | Code gọi CLI có thật | Chưa GPU-live verified |
| Blender export script | Code có thật | Chưa worker-headless verified |
| Wan2.2 generative video | Adapter copy video, chưa inference | **CHƯA** |
| MoVerse camera refinement | Status/flag, chưa inference | **CHƯA** |
| AI QC trên Pages | Sinh điểm random | **CHƯA, cần khóa** |
| AI QC backend | So sánh chưa đúng đầu ra | **CHƯA** |
| GitHub Pages Studio | UI dùng Canvas preview độc lập | Chưa tích hợp 3D backend |
| Auth/tenant isolation | Chưa có ở API | **CHƯA** |
| Docker clean/release CI | Cấu hình có lỗi đáng ngờ, chưa run | **CHƯA** |

**Next action mặc định:** **PHASE 00**, ngay sau đó xử lý `BUG-001`–`BUG-009` của **PHASE 01**. Không nhảy lên Wan2.2/MoVerse trước khi AI correctness và base architecture đạt gate.

---

## 14. Registry công nghệ nguồn (chỉ tham khảo, phải kiểm tra license/version)

- COLMAP — https://github.com/colmap/colmap
- Nerfstudio — https://github.com/nerfstudio-project/nerfstudio
- Blender — https://github.com/blender/blender
- Wan2.2 — https://github.com/Wan-Video/Wan2.2
- MoVerse — https://github.com/Orange-3DV-Team/MoVerse
- DUSt3R — https://github.com/naver/dust3r (**non-commercial license restrictions: verify**)
- FFmpeg — https://github.com/FFmpeg/FFmpeg
- Three.js — https://github.com/mrdoob/three.js

Không tự kết luận giấy phép checkpoint/model từ giấy phép source code; phải có bảng `version/checkpoint/license/commercial rights/redistribution/decision` trước khi bundling.

---

## 15. Thước đo trạng thái cho từng phase — bảng cập nhật bắt buộc

Sử dụng mẫu sau trong `PROJECT_STATUS.md` sau mỗi merge:

| Phase | State | Last PR/commit | Test evidence | Dataset/artifact | Owner | Blocker |
|---|---|---|---|---|---|---|
| P00 | NOT_STARTED | — | — | — | — | — |
| P01 | NOT_STARTED | — | — | — | — | P00 |
| P02 | NOT_STARTED | — | — | — | — | P00 |
| P03 | NOT_STARTED | — | — | — | — | P01/P02 |
| P04 | NOT_STARTED | — | — | — | — | P03 |
| P05 | NOT_STARTED | — | — | — | — | P03/P04 |
| P06 | NOT_STARTED | — | — | — | — | P03/P04 |
| P07 | NOT_STARTED | — | — | — | — | P06 + GPU |
| P08 | NOT_STARTED | — | — | — | — | P03/P05/P06 |
| P09 | NOT_STARTED | — | — | — | — | P01/P07/P08 + GPU/license |
| P10 | NOT_STARTED | — | — | — | — | P05–P09 |
| P11 | NOT_STARTED | — | — | — | — | P10 |

State hợp lệ: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `GATE_PASSED`, `REOPENED`. **Không dùng tỷ lệ % tự ước đoán để tuyên bố GATE_PASSED.**

---

### Kết luận

**Chiến lược chính thức:** sửa tính trung thực + bảo mật → build sạch → ổn định queue/contracts → CPU video tin cậy → camera path duy nhất → COLMAP/Nerfstudio/Blender live → UI thống nhất → AI tùy chọn có kiểm định → benchmark và phát hành. Đây là lộ trình để sản phẩm tiến gần trải nghiệm Twinmotion trong giới hạn vật lý của **ảnh tĩnh đầu vào**, không phải tạo một UI hào nhoáng với engine giả.
