# HYBRID AUTO 3D MODE — Đặc tả sản phẩm & kỹ thuật

> **Repository:** https://github.com/hieudang99dd/AI-Video-/  
> **Trạng thái:** ĐẶC TẢ ĐỀ XUẤT; chưa phải chức năng đã triển khai.  
> **Nguồn ưu tiên:** MASTER_REFACTOR_PLAN.md là kế hoạch chuẩn cho P00–P11; SKILL.md và PROJECT_STATUS.md là quy trình và bằng chứng thực hiện. Tài liệu này bổ sung yêu cầu tính năng, không thay thế các phase/gate đã có.  
> **Cơ sở kiểm tra:** Nhánh refactor/p00-local-verification, phát triển tiếp từ draft PR #3 → draft PR #4. Agent phải kiểm tra lại HEAD, trạng thái PR và khác biệt trước khi sửa mã.

## 0. Quyết định sản phẩm

AI-Video phục vụ hồ sơ Civil 3D / InfraWorks, bao gồm **ảnh chụp cùng công trình ở nhiều góc**, **ảnh ở các vị trí khác nhau trong một nhóm nội dung**, và **mô hình 3D gốc tùy chọn (FBX, GLB/glTF)**.

Workflow chuẩn:

1. Người dùng tạo dự án, tạo nhóm *Tổng quan / Tuyến chính / Cầu vượt / Nút giao / Thoát nước / ATGT* hoặc nhóm tự đặt.
2. Người dùng chọn hoặc kéo ảnh từ PC vào từng nhóm; đổi thứ tự nhóm, ảnh; gắn ghi chú, lý trình, ảnh bắt buộc sử dụng. Ảnh có thể được tham chiếu ở nhiều nhóm, không nhân bản file gốc.
3. Hệ thống kiểm tra dữ liệu và **tách mỗi nhóm thành nhiều subscene** khi ảnh chụp thuộc những địa điểm không kết nối về hình học.
4. Phân tích từng subscene; đề xuất **SOURCE_MODEL_3D / RECONSTRUCTED_3D / DEPTH_25D / SOURCE_2D** dựa trên bằng chứng thực tế.
5. Người dùng duyệt/khóa lựa chọn. AI/rule engine lập storyboard theo đúng thứ tự nhóm, chọn shot và camera an toàn; mọi thông số kỹ thuật phải lấy từ nguồn có thể truy xuất.
6. Xem trước, chỉnh camera, timeline, chú thích, nhạc/lời dẫn; xuất video **MP4 thật**, QC khung hình và ghi provenance.

**Nguyên tắc: tự phân loại nhưng không tự bịa hình học, không giả lập thành công, không thay đổi thông tin kỹ thuật của công trình.**

### 0.1. Phân biệt bốn loại cảnh

| Effective mode | Nguồn | Có góc nhìn 3D mới? | Cam kết |
|---|---|---|---|
| SOURCE_MODEL_3D | Mesh gốc FBX/GLB/IFC đã chuyển đổi | Có, trong phạm vi mô hình | Hình học theo dữ liệu nguồn, phải kiểm tra transform/vật liệu/LOD |
| RECONSTRUCTED_3D | Ảnh đa góc được đăng ký camera + tái dựng | Có, trong vùng được quan sát và engine hỗ trợ | Không đồng nghĩa đúng hình học CAD/BIM; có thể không có kích thước tuyệt đối |
| DEPTH_25D | Ảnh + depth ước lượng | Có parallax hạn chế, không có đầy đủ mặt khuất | Chỉ minh họa, biên độ camera nhỏ và kiểm soát biến dạng |
| SOURCE_2D | Ảnh gốc | Không; pan/zoom/crop/transitions | An toàn nhất khi ảnh rời rạc hoặc nội dung yêu cầu trung thực |

Một file camera-path JSON hay hình point-cloud trang trí **không chứng minh** hệ thống đã render 3D. Một bộ 3D Gaussian Splats cũng **không được gọi là GLB** nếu chưa có mesh chuyển đổi thực.

## 1. Hai chế độ vận hành, không ép người dùng cài phần mềm

### 1.1. LOCAL BROWSER — mặc định

- Chọn file ảnh/GLB/FBX từ PC bằng File API; **đọc tại máy**, không upload lên server.
- Quản lý nhóm, thumbnail, metadata, IndexedDB/project JSON backup; không có quyền xem toàn bộ ổ đĩa nếu chưa được người dùng chọn.
- Storyboard rule-based, preview 2D; GLB 3D bằng Three.js khi engine sẵn sàng; browser 2.5D chỉ khi depth model và khả năng trình duyệt đã được đo.
- WebCodecs/H.264+MP4 muxer cần capability probe; WebM từ MediaRecorder **không được đổi đuôi thành MP4**.
- Không hứa COLMAP/3DGS GPU local trên PC công ty khi chưa có bản native/worker thực tế được phép sử dụng.

### 1.2. REMOTE COMPUTE — tùy chọn, cần đồng ý

- Chỉ khi người dùng chủ động chọn “Tái dựng 3D trên máy chủ”, trình duyệt mới upload đúng bộ ảnh được chọn.
- Backend FastAPI xác thực/ủy quyền dự án; object storage cô lập tenant; hàng đợi bất đồng bộ; GPU recon worker dùng COLMAP + 3DGS hoặc pipeline đã kiểm chứng.
- Render worker có thể ghép video bằng FFmpeg; thu phí người dùng bằng 0 **không có nghĩa** GPU server không phát sinh chi phí.
- Không vượt qua chính sách IT trên máy công ty; thông báo lưu trữ, retention và cấp phép dữ liệu trước upload.

## 2. Kiến trúc tổng thể

~~~text
NEXT.JS WEB STUDIO (single authoritative frontend)
  ├─ Group Library / Metadata / Drag-Reorder
  ├─ Analysis Dashboard (capability + evidence; no invented scores)
  ├─ Storyboard Editor / Camera Inspector / Timeline
  └─ Export Panel / Job Monitor / QC
            |
      Local-first store  <------- source files chosen by user
            |                               |
            +--------- Image ingestion -----+
            +--------- Model import [FBX/GLB] ----> Three.js scene viewer
            |
     Group Analyzer / Subscene Graph
       ├─ Input checks + duplicates + blur
       ├─ Visual feature matches + geometric inliers
       ├─ Scene clustering (different KM/location = different subscene)
       ├─ SfM camera registration [optional real GPU worker]
       ├─ Reconstruction QA / depth QA
       └─ Mode Decision with reasons and provenance
            |
     Storyboard Planner + Single CameraPath Contract
            |
    +-------+----------+----------------+
    |                  |                |
 Source 2D          Depth 2.5D    True 3D renderer
    |                  |           model / verified recon
    +------------------+----------------+
                       |
            Timeline compositor + sound + text
                       |
        Frame-accurate encoder / ffprobe / decode QC
                       |
         Real MP4 + shot manifest + source provenance
~~~

### 2.1. Gắn với repo đã kiểm tra

- apps/web/app/page.tsx: hiện quản lý projects/assets/shots, fetch tới NEXT_PUBLIC_API_URL/localhost:8000. **Không được tạo một web mock khác làm sản phẩm chính**.
- apps/web/package.json: Next.js 16.3.3, React 19.1.1; chưa có Three.js trong nhánh đã kiểm tra.
- apps/api/app/api/routes.py: API hiện có; mở rộng versioned endpoints giữ backward compatibility.
- packages/camera_math, packages/colmap, packages/geometry, packages/path_validation, packages/scene_grouping: đọc lại implementation và tái sử dụng; không mặc định các adapter này đang chạy inference/geometry thật.
- tests/unit, tests/integration: mở rộng regression, bảo vệ P0 security/truthfulness.
- Root index.html và docs/index.html: static demo, **không phải** backend 3D production. Đừng marketing mock là năng lực thật.

**Không merge trực tiếp vào main.** Feature branch nên được tạo từ head tương ứng với PR #4 nếu PR #3/#4 vẫn đang stacked; giải quyết cơ chế merge/rebase sau đó, tránh vô tình loại bỏ thay đổi.

## 3. Image Group khác 3D Subscene

Ví dụ nhóm “Tuyến chính” có 12 ảnh ở Km0, Km3, Km8 và Km14; hệ thống **không** ghép thành một không gian 3D liên tục chỉ vì chúng chung tên nhóm.

Data relationship:

~~~text
Project
 └─ Group (narrative order)
      ├─ Image assets (ordered, multigroup references allowed)
      ├─ Optional source-model references
      └─ Subscene 1..N (geometrically coherent capture area)
            ├─ matching / registration evidence
            ├─ 3D representation if successful
            ├─ effective mode
            └─ Shots 0..N
~~~

### 3.1. Image ingestion

- Validate signature + actual decode JPG/PNG/WebP, dimensions, count, bytes, decompression bombs and malformed files; immutable originals, SHA-256, stable ID.
- Deduplicate identical bytes without collapsing narrative references.
- Normalize EXIF orientation in preview; preserve original and provenance; scrub sensitive GPS if privacy demands.
- User metadata: group name, group order, description, station, object location, “must include”, priority image, approved technical description, excluded images, locked order.
- UI per group: upload/click/drag, reorder, move/copy reference to other group, assign shot, add subscene label, delete reference vs permanently delete original (distinct actions).
- Model import: GLB/glTF preferred for web. Three.js FBXLoader may support compatible FBX; complex FBX/materials/textures may require approved conversion worker; detect missing external textures.

### 3.2. Matching and clustering

Graph nodes = image asset IDs, edges = verified feature correspondences with geometric consistency. Build scene hypotheses by connected components, geometry checks and camera pose viability. Reject groups with only perceptual similarity but no parallax (identical crops/zooms), repeating patterns, insufficient baseline or degenerate camera configurations.

For each subscene report measured values (if actually measured): registered images, matched edges, geometric inlier counts, reprojection errors, coverage, parallax, evidence version and fallback reasons. **Never fabricate confidence 0.9/91%.**

## 4. Mode Decision Engine — policy & states

Requested mode: AUTO | SOURCE_MODEL_3D | RECONSTRUCTED_3D | DEPTH_25D | SOURCE_2D.

Effective mode: SOURCE_MODEL_3D | RECONSTRUCTED_3D | DEPTH_25D | SOURCE_2D | UNAVAILABLE.

Run status: NOT_RUN | QUEUED | RUNNING | COMPLETED | FAILED | CANCELLED. Evidence: NOT_RUN | VERIFIED | INCONCLUSIVE | FAILED. Capability: AVAILABLE | UNAVAILABLE | UNKNOWN.

Rules, in order:

1. If a real source-model 3D is mapped to the subscene AND model load, coordinate, draw and camera-path QA pass → SOURCE_MODEL_3D.
2. Else if real multi-view reconstruction **completed**, a compatible renderable scene exists AND pose/novel-view/camera QA pass → RECONSTRUCTED_3D.
3. Else if actual depth scene exists, depth QA passes and requested motion is within safe bounds → DEPTH_25D.
4. Else if valid source images exist → SOURCE_2D.
5. If none works → UNAVAILABLE, explain missing/corrupt assets.

**Mode requested by user is not the mode executed.** A manual 3D override means “attempt 3D and show blockers”, **not** bypassing checks. A shot requiring exact geometry must be blocked for review if 3D fails, not silently down-converted to fabricated visuals.

Calibrate thresholds on real dataset; there is no universal valid cutoff for 3D camera registration, depth confidence or reconstruction readiness.

### 4.1. Report example (schema illustration, no measured score)

~~~json
{
  "subsceneId": "scene-cau-01",
  "imagesSubmitted": 30,
  "registeredCameras": null,
  "reprojectionErrorPx": null,
  "modeSuggested": "SOURCE_2D",
  "modeEffective": "SOURCE_2D",
  "evidenceStatus": "NOT_RUN",
  "reconstructionJobId": null,
  "sceneArtifactId": null,
  "reasonCodes": ["RECONSTRUCTION_NOT_EXECUTED"],
  "warnings": ["No true-3D claim available"]
}
~~~

## 5. Storyboard AI và quy tắc dựng

Input: project metadata được người dùng xác nhận; group order; per-subscene analysis evidence; shot constraints; target duration; selected images; available 3D objects and spatial bounds.

Output: shot list, source/mode, camera type, selected images, narration draft (optional), titles, duration, timeline, transition, model reference, camera path and risk notes.

### Shot grammar

- SOURCE_MODEL_3D: FLYOVER, ORBIT, ROUTE_FOLLOW, DOLLY, BRIDGE_REVEAL, DETAIL_PUSH.
- RECONSTRUCTED_3D: ORBIT_BOUNDED, ARC, REGISTERED_PATH, DOLLY_BOUNDED (chỉ trong vùng scene có dữ liệu).
- DEPTH_25D: PARALLAX_DRIFT, DEPTH_PUSH, LAYERED_REVEAL với dịch chuyển nhỏ.
- SOURCE_2D: KEN_BURNS, PAN, CROP, TECHNICAL_CALLOUT, PHOTO_CUT.

Rules: giữ thứ tự nhóm theo yêu cầu; giữ ảnh được lock; không bịa số liệu thiết kế hay chuyển camera xuyên mặt đất; tránh đảo hướng nhìn đột ngột, tăng FOV cực đoan hoặc “bay” ngoài scene; ngắt đoạn tuyến khác vị trí bằng cut/graphic transition thay vì giả bay liên tục. Sum thời lượng phải khớp target, thống nhất quy tắc transition overlap.

Kịch bản AI dùng LLM nếu thực sự chạy inference; phiên bản offline template/rule engine phải ghi là AUTO STORYBOARD, không tự gọi là AI sinh ngôn ngữ.

### 5.1. Camera contract dùng chung

~~~json
{
  "schemaVersion": "camera-path/v1",
  "shotId": "shot-001",
  "representation": "SOURCE_MODEL_3D",
  "coordinateSpace": "SCENE_LOCAL_METERS",
  "sourceTransformId": "tx-001",
  "durationSec": 8,
  "fps": 30,
  "keyframes": [
    {"timeSec": 0, "position": [10, 50, 100], "target": [0, 0, 0], "fovDeg": 42, "ease": "easeInOut"},
    {"timeSec": 8, "position": [80, 32, 40], "target": [30, 0, 0], "fovDeg": 38, "ease": "easeInOut"}
  ],
  "validation": {"status": "NOT_RUN", "collisionCount": null}
}
~~~

Vị trí trên là minh họa; production path phải lấy bounds thực. Preview/render/export dùng **cùng** đường camera và sampling timestamp, không tạo hai trajectory mâu thuẫn.

## 6. Data model và API

Entities: Project, Asset, Group, GroupAsset, Subscene, SceneAsset, AnalysisRun, ModeDecision, Storyboard, Shot, CameraPath, RenderJob, OutputArtifact, QualityReport, ConsentReceipt, AuditEvent. IDs phải ổn định, project-scoped, revision/version và SHA-256 của bytes.

### 6.1. Contract mẫu

~~~json
{
  "schemaVersion": "hybrid-auto-3d/v1",
  "projectId": "project-demo",
  "privacyMode": "LOCAL_ONLY",
  "groups": [
    {
      "id": "group-cau",
      "title": "Cầu vượt",
      "sortIndex": 2,
      "description": "Ảnh quay quanh cầu",
      "orderedAssetIds": ["asset-1", "asset-2"],
      "subsceneIds": ["subscene-1"],
      "modeRequested": "AUTO",
      "lockedOrder": true
    }
  ],
  "subscenes": [
    {
      "id": "subscene-1",
      "groupId": "group-cau",
      "analysisStatus": "NOT_RUN",
      "modeSuggested": null,
      "modeEffective": "SOURCE_2D",
      "sceneAssetId": null,
      "evidenceStatus": "NOT_RUN"
    }
  ],
  "storyboard": {"status": "DRAFT", "shotIds": []}
}
~~~

### 6.2. Backend endpoints đề xuất (sau RBAC)

| Method | Path | Chức năng |
|---|---|---|
| POST | /api/v1/projects/{id}/groups | Tạo nhóm |
| PATCH | /api/v1/projects/{id}/groups/{groupId} | Tên, order, mô tả, lock |
| POST | /api/v1/projects/{id}/groups/{groupId}/assets | Liên kết ảnh với nhóm |
| POST | /api/v1/projects/{id}/analysis-runs | Idempotent async analysis |
| GET | /api/v1/projects/{id}/analysis-runs/{runId} | Progress/evidence thực |
| POST | /api/v1/projects/{id}/mode-decisions | Duyệt/override có audit log |
| POST | /api/v1/projects/{id}/storyboard/generate | Rule based; LLM optional |
| PATCH | /api/v1/projects/{id}/storyboard/shots/{shotId} | Duyệt/chỉnh shot |
| POST | /api/v1/projects/{id}/render-jobs | Async render |
| GET | /api/v1/projects/{id}/render-jobs/{renderId} | Job + QC + verified download |

Require project-scoped authn/authz and negative IDOR tests, Idempotency-Key, optimistic concurrency / revision, limits and async lease/heartbeats. Do not render long GPU jobs inside HTTP request. Do not expose local filesystem path.

## 7. Renderer / Export / QC

- 3D renderer draws **actual** GLB geometry or verified reconstructed representation, with real geometry-aware camera.
- 2.5D requires actual depth and hole/artifact validation; 2D always uses source pixel values.
- Timeline renderer freezes source hashes + engine/mode/camera paths, renders deterministic frame time = frameIndex/FPS; knows transition overlap semantics.
- Browser-only path tests WebCodecs codec support and muxer; remote path uses FFmpeg; codec/container must match actual file.
- MP4 QC: decode success, codec, frame count, dimensions, FPS, duration/timestamps, audio presence if requested, missing files/black or duplicate frames where measurable, provenance and effective backend. Status = PASS / FAIL / INCONCLUSIVE / NOT_RUN.
- Output bundle: actual MP4, project_manifest.json, shot_manifest.json, camera_paths.json, analysis_report.json, quality_report.json, provenance.json, checksums.sha256. Links shown only when files exist.
- Re-render invalidation on changes to source, camera, asset mapping, subtitles, presets or renderer versions.

## 8. UI/UX — ghép với prototype

Four sections/tabs in one main Studio:

**A. Thư viện nhóm ảnh:** left groups with add/reorder, center thumbnail grid/upload, right inspector for description, mode request, selected image notes; place a clear LOCAL ONLY vs SERVER DATA TRANSFER indicator.

**B. Phân tích Auto 3D:** cards per **subscene**, show status NOT_RUN / ANALYZING / READY / INCONCLUSIVE; evidence and reason codes, retry/approve/override; if backend absent, display capability unavailable, not fabricated 3D success.

**C. Storyboard:** dynamic timeline, ordered/locked shots, mode tags, camera presets, start/end and cut/crossfade; allow edit, move shot up/down, play source-2D preview. Camera controls disabled with explanations if corresponding render engine not yet available.

**D. Export:** preview/final profiles, playback/codec gate, privacy notice, real render receipt and download only after verified; no pretend MP4 button.

Style: technical BIM professional dark UI, navigation compact, cyan/indigo highlights, clear hierarchy and density, keyboard/reduced-motion, no redundant empty panels.

State machine: EMPTY → GROUPS_READY → ASSETS_READY → ANALYSIS_PENDING/AVAILABLE → REVIEW_REQUIRED → STORYBOARD_DRAFT → APPROVED → RENDER_QUEUED → RENDERING → OUTPUT_VERIFIED / FAILED. Capability state and job state are separate.

## 9. Delivery order and acceptance gates

These feature increments **do not rename or bypass** P00–P11 / G00–G11 in MASTER_REFACTOR_PLAN.md.

| Feature | Triển khai | Tiêu chí nghiệm thu |
|---|---|---|
| H0 | Branch + preserve P00/P01 regression | New branch, no writes to main, docs note blockers |
| H1 | Group Manager local-first | 5 groups, upload/reorder/move images, reload project, no network file upload in Local Only |
| H2 | Rule storyboard + verified 2D MP4 | Timeline 30s, real decodable video and frame/timestamp/QC report |
| H3 | FBX/GLB importer + Three.js + camera | Load real model, inspect object bounds, orbit and route follow visible in actual rendered video |
| H4 | Subscene graph + 2.5D | Detect distinct sites in same group, reject duplicated pseudo-overlap, safe depth fallback |
| H5 | Optional remote COLMAP/3DGS | Consciously consented data transfer, actual GPU job with SfM/representation/camera pose receipts; failure datasets properly rejected |
| H6 | Unified Hybrid MP4 | Mixed 3D + 2.5D + 2D timeline decodes, user-approved storyboard, provenance and no silent mode substitution |

### Mandatory test datasets

- Single image or multiple unrelated locations → never claim 3D.
- Duplicates/zoomed crops → do not treat as multi-view camera coverage.
- Multi-view real bridge / junction scene → register pose, scene, render and evaluate with observed evidence.
- Source-model GLB and at least one real project export where permitted → verify orientation, units, materials, geospatial/local origin, scene bounds.
- Long road model and fragmented segments → prevent float precision/camera warping.
- Invalid/oversize/corrupt image, zip path traversal and malformed FBX → fail closed.
- Unauthorized multi-tenant project/group/render access → 401/403.
- Chrome/Edge browser codec unavailable → explanatory fallback, no mislabeled MP4.
- Output clip must be independently decoded; no QC random number, no fabricated success badge.

## 10. Security, privacy and operating boundaries

- Server mode cannot reuse existing production-wide token as proof of project RBAC. Enforce tenant scoping in every route, artifact and job.
- Per-project upload authorization and consent, encrypted transport, quotas, retention/deletion, redact EXIF/geolocation according to policy. Do not train on user/company imagery without separate explicit consent.
- File size/pixel/model/texture/resource caps; safe filenames, sanitized overlay text, image MIME validation, dependency CVE review.
- Local Browser mode must be audited to ensure no project file/frame bytes leave the machine. Browser website first download is not project data upload.
- Scale ambiguous recon cannot be labeled metric. AI-generated geometry must not be used for Civil 3D dimensional checks.
- GPU cloud and hosted storage cost real money even if product offers free end-user access.

## 11. Definition of Done and reporting

Every feature PR contains issue ID, HEAD SHA, changed files, test commands/results, environment/browser, dataset license/hash, output clip with ffprobe/decode evidence, failed negative tests and open risks. Update PROJECT_STATUS.md with evidence; don't mark G00/G01 or 3D as passed from mock or CI limited to CPU.

Existing draft PR #3 and PR #4 contain truthfulness/security/verification changes; reconcile stacked dependencies before feature merge. Keep source originals, migration rollback and backward compatibility.

## 12. Companion files

1. prototypes/hybrid-auto-3d-studio.html — interactive **prototype**, not live analysis or MP4 renderer; features and stub behavior must be clearly labeled.
2. AGENT_IMPLEMENT_HYBRID_AUTO_3D.md — coding agent prompt with phase-by-phase tasks, tests and DoD.

**Product mantra:** Group is for narrative; subscene is for geometry; evidence decides mode; storyboard decides story; one camera contract and one verified render output decide quality.
