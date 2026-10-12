# Quy trình ghép các repository mã nguồn mở vào AI-Video-

> Tài liệu triển khai cho repository [hieudang99dd/AI-Video-](https://github.com/hieudang99dd/AI-Video-). Mục tiêu là tận dụng có chọn lọc các dự án nguồn mở để hoàn thiện pipeline **ảnh → tái dựng 3D → camera path → render → MP4**, đồng thời giữ nguyên kiến trúc, hợp đồng dữ liệu và cơ chế fallback an toàn của AI-Video-.

## 1. Nguyên tắc bắt buộc

1. **Không ghép nguyên repository.** Không copy toàn bộ thư mục, không merge nguyên lịch sử Git, không thay thế app hiện tại bằng một ứng dụng desktop khác.
2. **Giữ AI-Video- làm ứng dụng chủ.** Các repository bên ngoài chỉ cung cấp engine, thuật toán tham khảo, cách tổ chức pipeline, UI pattern hoặc adapter được kiểm duyệt.
3. **Không viết lại thứ đã có.** Trước khi thêm code, đọc file hiện tại và test liên quan. Nếu tính năng đã có, chỉ sửa phần thiếu hoặc lỗi.
4. **Một engine 3DGS chính trong giai đoạn đầu.** Dùng COLMAP + Nerfstudio/Splatfacto làm đường chính. Không đồng thời tích hợp nhiều engine 3DGS trước khi đo được chất lượng của engine chính.
5. **Không giả kết quả hình học.** Nếu COLMAP/3DGS thiếu dependency, ảnh không đủ overlap hoặc quality gate thất bại, phải trả lỗi rõ ràng hoặc fallback sang 2D_IMAGE_CAMERA/2.5D. Không gọi video 2D là camera bay 3D.
6. **Giữ một hợp đồng camera path duy nhất.** Schema chuẩn hiện tại nằm trong packages/geometry/camera_path.py. Mọi UI hoặc renderer mới phải chuyển đổi về schema này; không để mỗi repo dùng một định dạng không tương thích.
7. **Không lưu file nặng vào Git.** Ảnh gốc, COLMAP database, point cloud, checkpoint, frame render và MP4 phải nằm trong storage của ứng dụng hoặc object storage, không commit vào source repo.
8. **Kiểm tra giấy phép trước khi sao chép code, asset, model hoặc binary.** Tham khảo docs/DEPENDENCY_LICENSE_GATE.md và docs/EXTERNAL_REPO_SOURCE_MAP.md. README không thay thế việc kiểm tra LICENSE của từng dependency.
9. **Tích hợp qua adapter và process boundary.** Engine ngoài nên được gọi bằng CLI/subprocess hoặc API ổn định; không kéo toàn bộ framework vào import graph của FastAPI nếu không cần.
10. **Không bắt đầu Hybrid GPU Router ở giai đoạn này.** Trước tiên phải có benchmark end-to-end tái dựng và xuất MP4 thật trên GPU. Local GPU Agent và GPU thuê là giai đoạn sau.

## 2. Trạng thái hiện có trong AI-Video-

Repository đã có sẵn các thành phần sau; agent phải đọc và tận dụng chúng trước khi tạo file mới.

| Thành phần hiện tại | Đường dẫn trong AI-Video- | Trách nhiệm |
|---|---|---|
| Hợp đồng backend geometry | apps/api/app/services/geometry_backend.py | Interface GeometryBackend, capability gate, gọi COLMAP và Nerfstudio, trả lỗi có thể xử lý |
| Chuẩn bị dataset Nerfstudio | packages/geometry/nerfstudio.py | Tạo layout images/colmap/sparse/0 và transforms.json |
| Chuyển đổi hệ tọa độ | packages/geometry/coords.py | Quy ước pose và chuyển đổi tọa độ canonical ↔ Nerfstudio |
| Camera path schema và sampler | packages/geometry/camera_path.py | Keyframe, quaternion, timestamp, easing, nội suy, serialization và camera-path JSON |
| Chọn keyframe từ camera đã đăng ký | packages/geometry/keyframes.py | Lựa chọn 2–3 view có baseline phù hợp; không tự bịa camera |
| COLMAP repository | packages/colmap/repository.py | Đọc dữ liệu tái dựng và thống kê camera/point cloud |
| Scene grouping | packages/scene_grouping/grouper.py | Gom ảnh theo bằng chứng hình học, tránh gom chỉ vì ngữ nghĩa giống nhau |
| Kiểm tra camera path | packages/path_validation/validator.py | Kiểm tra độ mượt, giới hạn, clearance proxy, confidence và rejection reasons |
| Capability detection | apps/api/app/services/capabilities.py | Phát hiện FFmpeg, COLMAP, ns-train/ns-render và CUDA thật sự có sẵn |
| Worker render | apps/api/app/workers/render_worker.py | Xử lý RenderJob ngoài HTTP request, progress, cancel và lỗi |
| Render và mã hóa video | apps/api/app/services/renderer.py | Fallback an toàn, gọi geometry render, ghép frame và xuất MP4 bằng FFmpeg |
| API contract | apps/api/app/schemas/contracts.py | Schema request/response hiện tại |
| Database models | apps/api/app/models/entities.py | Project, ImageAsset, Shot, Scene, RenderJob; Shot đã có trường JSON keyframes |
| API routes | apps/api/app/api/routes.py | API v1 cho project, asset, shot, scene, job và capability |
| Giao diện hiện tại | apps/web/app/page.tsx | Next.js UI cho project, upload, phân tích, storyboard và render job |
| Benchmark | docs/BENCHMARK_DATASETS.md | Bộ trường hợp kiểm thử cần có |
| License gate | docs/DEPENDENCY_LICENSE_GATE.md | Theo dõi version, license, quyền thương mại và quyết định tích hợp |

### Điều chưa được coi là hoàn thành

Theo PROJECT_STATUS.md và PHASE0_CHECKLIST.md, không được tuyên bố Geometry Mode đã đạt chất lượng sản phẩm chỉ vì code adapter tồn tại. Cần chạy thành công pipeline thật với CUDA, COLMAP, Nerfstudio, FFmpeg và kiểm tra chất lượng trên dữ liệu benchmark.

Lưu ý kỹ thuật: khoảng cách từ camera đến sparse point cloud chỉ là **proxy** cho clearance, không phải chứng minh va chạm vật lý chính xác với bề mặt công trình. Nếu chưa có mesh/occupancy/depth đủ tin cậy, UI phải thể hiện mức độ không chắc chắn và không quảng cáo là collision detection tuyệt đối.

## 3. Repository nguồn và chính xác phần nên tận dụng

### 3.1. Nerfstudio — engine chính cho tái dựng và render camera path

Nguồn: [nerfstudio-project/nerfstudio](https://github.com/nerfstudio-project/nerfstudio)  
License của repository chính: Apache-2.0. Dependency, CUDA, checkpoint và model bổ sung vẫn phải được kiểm tra riêng.

**Các file nguồn cần đọc:**

- [README.md](https://github.com/nerfstudio-project/nerfstudio/blob/main/README.md) — quy trình ảnh/video → dataset → train → viewer → render.
- [nerfstudio/process_data/colmap_converter_to_nerfstudio_dataset.py](https://github.com/nerfstudio-project/nerfstudio/blob/main/nerfstudio/process_data/colmap_converter_to_nerfstudio_dataset.py) — cách chuyển kết quả COLMAP thành dataset.
- [nerfstudio/data/dataparsers/colmap_dataparser.py](https://github.com/nerfstudio-project/nerfstudio/blob/main/nerfstudio/data/dataparsers/colmap_dataparser.py) — quy ước đọc camera/ảnh từ COLMAP.
- [nerfstudio/models/splatfacto.py](https://github.com/nerfstudio-project/nerfstudio/blob/main/nerfstudio/models/splatfacto.py) — model 3D Gaussian Splatting của Nerfstudio.
- [nerfstudio/scripts/train.py](https://github.com/nerfstudio-project/nerfstudio/blob/main/nerfstudio/scripts/train.py) — entry point của lệnh train.
- [nerfstudio/scripts/render.py](https://github.com/nerfstudio-project/nerfstudio/blob/main/nerfstudio/scripts/render.py) — entry point render camera path.
- [nerfstudio/cameras/camera_paths.py](https://github.com/nerfstudio-project/nerfstudio/blob/main/nerfstudio/cameras/camera_paths.py) — quy ước camera path phía Nerfstudio.
- [nerfstudio/viewer/render_panel.py](https://github.com/nerfstudio-project/nerfstudio/blob/main/nerfstudio/viewer/render_panel.py) — tham khảo luồng tạo keyframe và thiết lập render trong viewer.
- [docs/reference/cli/ns_train.md](https://github.com/nerfstudio-project/nerfstudio/blob/main/docs/reference/cli/ns_train.md) — tham số CLI train.
- [docs/reference/cli/ns_render.md](https://github.com/nerfstudio-project/nerfstudio/blob/main/docs/reference/cli/ns_render.md) — tham số CLI render.

**Nên tận dụng:** lệnh CLI thực tế, format dataset, quy ước camera, cấu trúc output, config/checkpoint, cách tạo render camera path và thông báo lỗi.

**Không nên tận dụng:** copy cả source code Nerfstudio vào apps/api; fork model training khi chưa có lý do; hard-code đường dẫn máy cá nhân; giả lập output khi CLI không chạy.

**Cách tích hợp:** giữ adapter tại packages/geometry/nerfstudio.py và packages/geometry/coords.py; giữ GeometryBackend tại apps/api/app/services/geometry_backend.py. Gọi ns-train/ns-render qua subprocess có timeout, log, cancel và kiểm tra output. Pin version đã test trong tài liệu môi trường.

### 3.2. COLMAP — tái dựng camera pose và sparse point cloud

Nguồn: [colmap/colmap](https://github.com/colmap/colmap)

AI-Video- đã có lệnh COLMAP trong apps/api/app/services/geometry_backend.py và parser/repository tại packages/colmap/repository.py. Vì vậy, **không tạo pipeline COLMAP thứ hai**.

**Nên tận dụng:** cấu trúc database.db; model camera/ảnh/points3D; thống kê registered images; reprojection error; model_converter TXT/BIN; feature matching và mapper; log để giải thích vì sao ảnh không đăng ký được.

**Nơi lưu dữ liệu chạy:** trong workspace theo scene, ví dụ storage/projects/{project_id}/scenes/{scene_id}/. Các tên thư mục vật lý phải được resolve thông qua app/services/storage.py; không ghi đường dẫn tuyệt đối của máy công ty vào database.

**Chỉ cải tiến khi benchmark chỉ ra vấn đề:** loại ảnh trùng, chọn sequential matcher cho chuỗi ảnh/video phù hợp, điều chỉnh matcher hoặc ngưỡng chất lượng. Không giảm ngưỡng chỉ để ép một bộ ảnh yếu thành Geometry Mode.

### 3.3. OOOSplat — tham khảo pipeline orchestration, progress và xử lý video

Nguồn: [ooolabdev/ooosplat](https://github.com/ooolabdev/ooosplat)  
Code chính của OOOSplat dùng Apache-2.0; các engine và thư viện đi kèm có giấy phép riêng. Đây là app desktop Tauri/Rust/React, **không phải backend web để bê nguyên vào AI-Video-**.

**Các file nguồn cần đọc:**

- [src-tauri/src/pipeline/runner.rs](https://github.com/ooolabdev/ooosplat/blob/main/src-tauri/src/pipeline/runner.rs) — điều phối pipeline theo bước.
- [src-tauri/src/pipeline/progress.rs](https://github.com/ooolabdev/ooosplat/blob/main/src-tauri/src/pipeline/progress.rs) — biểu diễn và cập nhật tiến độ.
- [src-tauri/src/pipeline/state.rs](https://github.com/ooolabdev/ooosplat/blob/main/src-tauri/src/pipeline/state.rs) — trạng thái pipeline.
- [src-tauri/src/video/extract.rs](https://github.com/ooolabdev/ooosplat/blob/main/src-tauri/src/video/extract.rs) — trích frame từ video.
- [src-tauri/src/video/frame_plan.rs](https://github.com/ooolabdev/ooosplat/blob/main/src-tauri/src/video/frame_plan.rs) — kế hoạch lấy frame.
- [src-tauri/src/video/probe.rs](https://github.com/ooolabdev/ooosplat/blob/main/src-tauri/src/video/probe.rs) — đọc metadata media.
- [src/components/GaussianViewer/GaussianVideoExport.ts](https://github.com/ooolabdev/ooosplat/blob/main/src/components/GaussianViewer/GaussianVideoExport.ts) — tham khảo export video.
- [src-tauri/src/presets/pipeline_config.rs](https://github.com/ooolabdev/ooosplat/blob/main/src-tauri/src/presets/pipeline_config.rs) — tham khảo preset chất lượng.
- [licenses/THIRD_PARTY_NOTICES.txt](https://github.com/ooolabdev/ooosplat/blob/main/licenses/THIRD_PARTY_NOTICES.txt) — kiểm tra thông báo license bên thứ ba.

**Nên tận dụng:** cách chia stage; trạng thái queued/running/completed/failed/cancelled; progress theo stage; cancel/resume; preset Fast/Balanced/Detail; lưu log và metadata; xác nhận output trước khi báo thành công.

**Không nên tận dụng:** Tauri command layer, Rust app state, đường dẫn desktop riêng, bundle COLMAP/Brush/FFmpeg chưa kiểm duyệt license. AI-Video- đã có RenderJob và worker; chuyển ý tưởng phù hợp vào apps/api/app/workers/render_worker.py, apps/api/app/services/queue.py và renderer.py thay vì thêm một job manager khác.

### 3.4. Scene-Gaussian-Splat-Viewer — tham khảo giao diện camera path/timeline

Nguồn: [iab131/Scene-Gaussian-Splat-Viewer](https://github.com/iab131/Scene-Gaussian-Splat-Viewer)  
License: MIT; nếu sao chép code thì phải giữ copyright/license theo điều kiện MIT.

**Các file nguồn cần đọc:**

- [src/hooks/useCameraPath.js](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/src/hooks/useCameraPath.js) — state và thao tác camera path.
- [src/components/Timeline.jsx](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/src/components/Timeline.jsx) — timeline và scrubber.
- [src/components/KeyframeList.jsx](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/src/components/KeyframeList.jsx) — danh sách keyframe.
- [src/components/CameraPathControls.jsx](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/src/components/CameraPathControls.jsx) — điều khiển camera path.
- [src/components/ExportDialog.jsx](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/src/components/ExportDialog.jsx) — cài đặt xuất video.
- [src/utils/cameraUtils.js](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/src/utils/cameraUtils.js) — tiện ích camera.
- [src/utils/exportUtils.js](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/src/utils/exportUtils.js) — luồng export.
- [server.js](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/server.js) — tách viewer và server export.
- [README.md](https://github.com/iab131/Scene-Gaussian-Splat-Viewer/blob/main/README.md) — mô tả path JSON và tính deterministic export.

**Nên tận dụng:** timeline có thể kéo keyframe; scrubber để preview; thêm/xóa/sắp xếp keyframe; chế độ Edit/Preview/Export; progress/cancel; lưu path để render lại được; UI cấu hình resolution/FPS/duration.

**Điều chỉnh bắt buộc:** viewer nguồn dùng định dạng camera path riêng. Không lưu trực tiếp schema nguồn làm schema chính. Adapter UI phải chuyển đổi về packages/geometry/camera_path.py; quaternion dùng thứ tự xyzw; timestamps tăng nghiêm ngặt; mọi path phải qua PathValidator trước khi render.

**Nơi triển khai trong AI-Video-:** thêm component mới, dự kiến apps/web/app/components/CameraPathEditor.tsx và apps/web/app/components/SceneViewer.tsx. Đây là đường dẫn đề xuất, chưa phải file đã tồn tại. Dùng API FastAPI và RenderJob hiện có; video cuối vẫn render ở worker để giữ chất lượng và kết quả có thể tái lập.

### 3.5. KIRI-Maker — tham khảo preset chuyển động cinematic

Nguồn: [willjim/KIRI-Maker](https://github.com/willjim/KIRI-Maker)  
License: MIT theo LICENSE của repository.

**Các file nguồn cần đọc:**

- [js/app.js](https://github.com/willjim/KIRI-Maker/blob/main/js/app.js) — logic ứng dụng và các preset/chuyển động.
- [js/kiriLoader.js](https://github.com/willjim/KIRI-Maker/blob/main/js/kiriLoader.js) — cách tải scene 3DGS.
- [js/plyParser.js](https://github.com/willjim/KIRI-Maker/blob/main/js/plyParser.js) — đọc PLY trong trình duyệt.
- [README.md](https://github.com/willjim/KIRI-Maker/blob/main/README.md) — preset và workflow camera path.
- [LICENSE](https://github.com/willjim/KIRI-Maker/blob/main/LICENSE) — điều kiện license.

**Nên tận dụng:** danh mục preset như orbit, reveal, push-in/pull-out, fly-through; thao tác keyframe tùy chỉnh; preview trước export; tách Particle Mode/3D Reality nếu thực sự cần hai kiểu hiển thị.

**Không nên đưa vào giai đoạn đầu:** gesture control, particle effects và các hiệu ứng trang trí không phục vụ độ chính xác kỹ thuật. Chỉ lấy một số preset phù hợp công trình/hạ tầng, rồi sinh keyframe theo geometry và kiểm duyệt bằng PathValidator. Preset không được tự ý di chuyển camera xuyên tường hoặc ra ngoài vùng tái dựng.

**Nơi triển khai đề xuất:** packages/geometry/camera_presets.py. Đây là file mới dự kiến. Preset phải sinh CameraPathDocument theo schema chuẩn hiện tại.

### 3.6. SplatStream / video-to-splat — tham khảo phân phối scene trên web, làm ở giai đoạn sau

Nguồn: [thmsngyn/video-to-splat](https://github.com/thmsngyn/video-to-splat)  
License của code repository: BSD-3-Clause. Backend OpenSplat được nêu là AGPLv3; không chọn backend này cho sản phẩm thương mại nếu chưa có đánh giá pháp lý phù hợp.

**Các file nguồn cần đọc:**

- [DESIGN.md](https://github.com/thmsngyn/video-to-splat/blob/main/DESIGN.md) — tách offline pipeline và browser runtime.
- [ROADMAP.md](https://github.com/thmsngyn/video-to-splat/blob/main/ROADMAP.md) — phân biệt MVP với các tính năng đang phát triển.
- [METRICS.md](https://github.com/thmsngyn/video-to-splat/blob/main/METRICS.md) — cách định nghĩa benchmark.
- [src/splatstream/pipeline/ingest.py](https://github.com/thmsngyn/video-to-splat/blob/main/src/splatstream/pipeline/ingest.py) — lấy frame và chọn mẫu từ video.
- [src/splatstream/pipeline/sfm.py](https://github.com/thmsngyn/video-to-splat/blob/main/src/splatstream/pipeline/sfm.py) — SfM.
- [src/splatstream/pipeline/reconstruct.py](https://github.com/thmsngyn/video-to-splat/blob/main/src/splatstream/pipeline/reconstruct.py) — huấn luyện/tái dựng.
- [src/splatstream/pipeline/export_ply.py](https://github.com/thmsngyn/video-to-splat/blob/main/src/splatstream/pipeline/export_ply.py) — xuất PLY.
- [format/SPEC.md](https://github.com/thmsngyn/video-to-splat/blob/main/format/SPEC.md) — định dạng streaming riêng.
- [viewer/src/ply-loader.ts](https://github.com/thmsngyn/video-to-splat/blob/main/viewer/src/ply-loader.ts) — nạp PLY trên browser.
- [viewer/src/splat-renderer.ts](https://github.com/thmsngyn/video-to-splat/blob/main/viewer/src/splat-renderer.ts) — renderer browser.
- [server/serve.py](https://github.com/thmsngyn/video-to-splat/blob/main/server/serve.py) — phục vụ asset.

**Nên tận dụng ở giai đoạn sau:** frame sampling theo chuyển động; phân tách pipeline offline và viewer; lazy loading; LOD/streaming; đo thời gian tải frame đầu tiên, FPS, memory và ảnh hưởng băng thông.

**Không làm ngay:** không tạo định dạng .splx riêng trong Phase 0/1. Trước tiên sử dụng output Nerfstudio/PLY hiện có. Chỉ cân nhắc streaming khi scene lớn làm viewer web tải chậm, và phải có benchmark chứng minh lợi ích.

### 3.7. Gaussian Splatting Lightning — nguồn so sánh, không phải engine thứ hai mặc định

Nguồn: [yzslab/gaussian-splatting-lightning](https://github.com/yzslab/gaussian-splatting-lightning)  
License chính: MIT; repository thông báo một số submodule và code lấy từ dự án khác có license riêng.

**Các file nguồn cần đọc:**

- [internal/dataparsers/colmap_dataparser.py](https://github.com/yzslab/gaussian-splatting-lightning/blob/main/internal/dataparsers/colmap_dataparser.py) — parser COLMAP.
- [internal/viewer/ui/render_panel.py](https://github.com/yzslab/gaussian-splatting-lightning/blob/main/internal/viewer/ui/render_panel.py) — tham khảo viewer/render controls.
- [render.py](https://github.com/yzslab/gaussian-splatting-lightning/blob/main/render.py) và [viewer.py](https://github.com/yzslab/gaussian-splatting-lightning/blob/main/viewer.py) — entry point render/viewer.
- [configs/colmap_exp.yaml](https://github.com/yzslab/gaussian-splatting-lightning/blob/main/configs/colmap_exp.yaml) — tham khảo cấu hình thử nghiệm.
- [LICENSE.md](https://github.com/yzslab/gaussian-splatting-lightning/blob/main/LICENSE.md) và [submodules/README.md](https://github.com/yzslab/gaussian-splatting-lightning/blob/main/submodules/README.md) — kiểm tra license.

**Nên tận dụng:** chỉ dùng làm đối chứng nếu Nerfstudio/Splatfacto không đạt tốc độ hoặc chất lượng trên benchmark. So sánh output, độ ổn định, VRAM và thời gian train trên cùng dataset.

**Không nên làm:** cài đồng thời nhiều framework huấn luyện vào production trước khi có quyết định dựa trên số liệu. Nếu thử, tạo adapter riêng và không thay GeometryBackend contract.

### 3.8. InstantSplat — nhánh thử nghiệm cho trường hợp ít ảnh

Nguồn: [NVlabs/InstantSplat](https://github.com/NVlabs/InstantSplat)  
License code chính: Apache-2.0; checkpoint, submodule và dependency phải được kiểm tra riêng.

**Các file nguồn cần đọc:**

- [README.md](https://github.com/NVlabs/InstantSplat/blob/main/README.md) — phạm vi phương pháp và cách chạy.
- [train.py](https://github.com/NVlabs/InstantSplat/blob/main/train.py) — training entry point.
- [render.py](https://github.com/NVlabs/InstantSplat/blob/main/render.py) — render.
- [scene/colmap_loader.py](https://github.com/NVlabs/InstantSplat/blob/main/scene/colmap_loader.py) — dữ liệu camera/scene.
- [utils/camera_utils.py](https://github.com/NVlabs/InstantSplat/blob/main/utils/camera_utils.py) — tiện ích camera.
- [LICENSE](https://github.com/NVlabs/InstantSplat/blob/main/LICENSE) — license code.

**Nên tận dụng:** làm prototype so sánh cho bộ ảnh ít, thiếu overlap hoặc cần tái dựng nhanh; đo chất lượng camera, độ phủ scene và chất lượng novel-view.

**Không nên dùng làm backend chính ngay:** đây là code nghiên cứu, cần kiểm tra đầy đủ checkpoint/dependency và khả năng bảo toàn hình học. Chỉ đưa vào sau khi tạo adapter tùy chọn và có benchmark riêng; không tự động thay thế COLMAP + Nerfstudio.

## 4. Dữ liệu nào nên tận dụng và dữ liệu nào không nên sao chép?

### 4.1. Nên tận dụng từ các repository nguồn

- **Mã nguồn thuật toán cần thiết:** chỉ phần nhỏ đã xác định rõ mục đích và license cho phép.
- **Cấu trúc schema:** camera path, export settings, job state, render metadata; phải chuyển đổi về contract của AI-Video-.
- **Cấu hình và lệnh CLI:** tham số engine, format input/output, flags, phiên bản đã kiểm thử.
- **Ý tưởng UX:** timeline, keyframe list, preview/export state, progress, cancel, resume.
- **Test pattern:** cách kiểm thử path serialization, deterministic export, cancellation, CLI error và chất lượng output.
- **Thông tin benchmark:** định nghĩa metric và cách đo; không chép số liệu của repo khác thành kết quả của AI-Video-.
- **Ví dụ dữ liệu nhỏ:** chỉ dùng nếu license cho phép, ghi rõ nguồn và dùng làm test fixture chứ không đưa vào dữ liệu production mặc định.

### 4.2. Không tự động sao chép hoặc commit vào Git

- Dataset ảnh/video của người khác khi chưa có quyền sử dụng.
- Checkpoint/model weights chỉ vì chúng tải được từ GitHub hoặc Hugging Face.
- Binary CUDA, COLMAP, FFmpeg, Brush hoặc engine đóng gói sẵn mà chưa kiểm tra điều kiện phân phối.
- Toàn bộ node_modules, virtualenv, cache, output training, database và video render.
- Thông tin credentials, token, API key, đường dẫn cá nhân hoặc log có dữ liệu nhạy cảm.
- Các file GPL/AGPL hoặc dependency có license riêng vào codebase mà chưa có quyết định kiến trúc/pháp lý.

### 4.3. Dữ liệu cần giữ lại trong pipeline của chính AI-Video-

| Dữ liệu | Nội dung cần giữ | Vị trí/đầu mối |
|---|---|---|
| Original assets | File gốc bất biến, filename, SHA-256, kích thước, metadata phân tích ảnh | ImageAsset, apps/api/app/services/storage.py |
| COLMAP workspace | database.db, sparse model, registered cameras, points3D, log và phiên bản COLMAP | Workspace riêng cho Scene dưới storage |
| Reconstruction report | số ảnh đầu vào/đăng ký, registered ratio, camera count, reprojection error, geometry confidence, thời gian, lỗi | Scene.diagnostics và RenderJob.provenance |
| Nerfstudio run | dataset đã chuẩn hóa, config, checkpoint/scene representation, engine version, stdout/stderr | Workspace riêng của scene; lưu URI chứ không nhúng binary vào DB |
| Camera path | schema_version, keyframes, position, quaternion xyzw, timestamp, lens, duration, FPS, resolution, easing, path type, confidence và metadata | CameraPathDocument; Shot.keyframes hoặc artifact JSON versioned |
| Path validation | score, sample metrics, clearance status, out-of-bounds, visibility/confidence và rejection reasons | RenderJob.provenance hoặc artifact validation JSON |
| Render outputs | frames cần thiết, MP4, codec, FPS, resolution, duration, file size, QC result | storage và RenderJob |
| Benchmark record | dataset ID, commit/version, config, thời gian, peak VRAM/RAM, registered ratio, output, lỗi và chất lượng | docs/BENCHMARK_DATASETS.md và report theo từng run |

Không lưu tất cả frame trung gian vô thời hạn. Định nghĩa retention/cleanup policy; giữ các artifact cần để debug, resume, audit hoặc render lại.

## 5. Quy trình tích hợp theo giai đoạn

### Giai đoạn 0 — đóng băng baseline và tạo nhánh làm việc

1. Đồng bộ repository AI-Video- về phiên bản mới nhất.
2. Tạo nhánh riêng, ví dụ feature/geometry-repo-integration.
3. Đọc README.md, SKILL_CANONICAL.md, PROJECT_STATUS.md, docs/ARCHITECTURE.md, docs/EXTERNAL_REPO_SOURCE_MAP.md và docs/DEPENDENCY_LICENSE_GATE.md.
4. Chạy toàn bộ test hiện có, lưu kết quả trước khi sửa.
5. Kiểm tra git status và không ghi đè thay đổi của người dùng.

Lệnh tham khảo từ thư mục gốc:

    git status
    git switch -c feature/geometry-repo-integration
    python -m pytest -q

**Điều kiện hoàn thành:** có baseline test; agent liệt kê file hiện có và file dự kiến sửa; không copy repository nguồn vào thư mục dự án.

### Giai đoạn 1 — kiểm tra môi trường GPU trên PC công ty

Cấu hình máy đã biết: RTX 5070 Ti 16 GB VRAM, RAM khoảng 64 GB. Cần xác minh phiên bản driver/CUDA/PyTorch thực tế; không suy luận chỉ từ tên GPU.

Chạy PowerShell:

    nvidia-smi
    python apps/api/scripts/check_gpu_env.py
    colmap -h
    ns-train --help
    ns-render --help
    ffmpeg -version

Kiểm tra thêm bằng Python rằng torch.cuda.is_available() là true, đọc được tên GPU và VRAM. Ghi lại version của Python, PyTorch, CUDA runtime, COLMAP, Nerfstudio, gsplat và FFmpeg.

**Điều kiện hoàn thành:** capabilities endpoint phản ánh đúng các công cụ có thật; thiếu tool nào thì báo thiếu tool đó. Chưa được đánh dấu Geometry Mode đạt chỉ vì lệnh có trong PATH.

### Giai đoạn 2 — xác minh pipeline geometry hiện có, không viết lại

1. Đọc apps/api/app/services/geometry_backend.py, packages/colmap/repository.py, packages/geometry/nerfstudio.py, packages/geometry/coords.py và packages/geometry/keyframes.py.
2. Chọn bộ ảnh benchmark có overlap tốt; dùng cùng ảnh và config cho mọi lần chạy.
3. Chạy COLMAP feature extraction → matching → mapping → model conversion.
4. Xác nhận registered images, camera poses, sparse points và reprojection metrics.
5. Xác nhận dataset layout của Nerfstudio đúng, đặc biệt images/ và colmap/sparse/0/.
6. Chạy ns-train với Splatfacto và lưu config/checkpoint/metadata.
7. Chạy ns-render camera-path và kiểm tra chuỗi frame đầu ra.
8. Gọi FFmpeg encoder hiện có để tạo MP4; kiểm tra output qua QC.
9. Lưu log, command/version, thời gian, VRAM/RAM và lỗi vào report benchmark.

**Không sửa nhiều module cùng lúc.** Nếu fail, xác định stage gây lỗi và tạo test/diagnostic riêng. Không dùng video fallback để tuyên bố Geometry Mode thành công.

**Điều kiện hoàn thành:** có ít nhất một video geometry render thật từ bộ ảnh có overlap tốt trên RTX 5070 Ti; có artifact và report để tái hiện.

### Giai đoạn 3 — chất lượng scene, grouping và keyframe

1. Đối chiếu kết quả thực tế với packages/scene_grouping/grouper.py và packages/geometry/keyframes.py.
2. Kiểm tra scene group chỉ được nối bằng bằng chứng matching hình học; không gộp hai nơi khác nhau chỉ vì cùng loại phòng/công trình.
3. Sinh keyframe từ registered views; giữ image_id, pose, confidence và baseline trong metadata.
4. Kiểm tra camera path bằng packages/path_validation/validator.py.
5. Phân biệt “unknown clearance” với “đã kiểm tra không va chạm”. Sparse point cloud không chứng minh đầy đủ bề mặt.
6. Nếu không đủ registered views/baseline hoặc path score dưới ngưỡng, giải thích lý do và fallback theo policy.

**Điều kiện hoàn thành:** test cho ảnh overlap tốt, ảnh thưa, ảnh đơn và ảnh từ hai scene rời nhau đều có kết quả đúng kỳ vọng; không có camera path được bịa ra khi geometry thiếu.

### Giai đoạn 4 — tích hợp timeline/camera path vào Web UI

Dùng Scene-Gaussian-Splat-Viewer để tham khảo interaction, không thay Next.js app.

1. Đọc các file nguồn trong mục 3.4.
2. Tạo component mới, dự kiến:
   - apps/web/app/components/SceneViewer.tsx
   - apps/web/app/components/CameraPathEditor.tsx
   - apps/web/app/components/CameraPathTimeline.tsx
   - apps/web/lib/cameraPath.ts
3. Dùng viewer để xem scene/pose và tạo keyframe; timeline để chỉnh thứ tự/thời gian; preview để xem camera path.
4. Thêm hoặc mở rộng API contract để đọc/ghi keyframes theo Shot hiện tại. Shot model đã có JSON field keyframes nhưng schema request/response phải được kiểm tra và đồng bộ.
5. Mọi dữ liệu UI gửi về API phải validate và chuyển sang CameraPathDocument; không lưu schema riêng của repo nguồn làm canonical schema.
6. Khi người dùng bấm Render, API tạo RenderJob; worker chạy validation, render và FFmpeg. Không render video dài trong HTTP request.
7. Dùng server render làm kết quả chính thức; browser preview chỉ để xem trước. Nếu browser hỗ trợ export không có nghĩa output đó tương đương render server.

**Điều kiện hoàn thành:** có thể tạo, sửa, lưu, tải lại và preview path; render từ path đã lưu tạo output tái lập; path không hợp lệ bị chặn với lý do rõ ràng.

### Giai đoạn 5 — thêm preset camera cinematic

1. Đọc KIRI-Maker README và js/app.js để lập danh sách preset phù hợp.
2. Tạo packages/geometry/camera_presets.py.
3. Triển khai một nhóm nhỏ ban đầu: slow push-in, pull-out, orbit nhẹ, reveal, lateral dolly và fly-through có giới hạn.
4. Preset chỉ được khởi tạo từ scene bounds, registered views và target/region đã xác định; không tự đoán kích thước thật của công trình.
5. Mọi preset phải tạo CameraPathDocument hợp lệ và qua PathValidator.
6. Thêm unit tests cho path type, timestamps, quaternion, bounds và path rejection.
7. Ghi rõ khi preset không thể tạo đường đi an toàn và đề xuất người dùng chỉnh keyframe hoặc chuyển sang 2D_IMAGE_CAMERA.

**Điều kiện hoàn thành:** mỗi preset có test, preview và render; không có preset nào bỏ qua geometry/path validation.

### Giai đoạn 6 — nâng chất lượng orchestration và khả năng phục hồi

1. Đọc OOOSplat runner/progress/state và ánh xạ ý tưởng vào RenderJob/worker hiện có.
2. Không tạo queue hoặc trạng thái job song song nếu chưa chứng minh cần thiết.
3. Mỗi stage cần có progress, start/end timestamp, version/config, log tail, cancel handling và failure reason.
4. Xác định stage nào có thể resume an toàn; không đánh dấu job completed khi MP4/QC chưa đạt.
5. Đảm bảo retry không ghi đè original images hoặc output của lần chạy đã hoàn tất.
6. Chỉ thêm cache khi có cache key dựa trên scene input hash + engine version + config; tránh tái sử dụng checkpoint sai scene.

**Điều kiện hoàn thành:** test cancel, retry, worker restart, lỗi engine, thiếu disk và output hỏng. Trạng thái DB phải phản ánh đúng trạng thái thực tế.

### Giai đoạn 7 — streaming/viewer tối ưu cho web

Chỉ bắt đầu sau khi geometry pipeline và camera editor đã ổn định.

1. Đo kích thước scene, thời gian tải và FPS của viewer hiện tại.
2. Nếu cần, nghiên cứu SplatStream: ingest/SfM/reconstruct, PLY loader, splat renderer, design, metrics và roadmap.
3. Bắt đầu với format scene đã có; không tạo .splx chỉ vì repo nguồn có định dạng riêng.
4. Nếu thực sự cần LOD/chunk streaming, viết ADR riêng mô tả format, security, caching, CDN, backward compatibility và license.
5. Tách viewer tải scene khỏi worker render MP4. Một scene viewer chạy mượt không tự động chứng minh render server đạt chất lượng.
6. Không đưa model training hoặc binary GPU vào trình duyệt.

**Điều kiện hoàn thành:** benchmark cho thấy cải thiện rõ ràng về thời gian tải/FPS/memory so với viewer ban đầu; không làm thay đổi output geometry/camera path.

### Giai đoạn 8 — thử engine nghiên cứu thay thế, nếu cần

Chỉ làm nếu Nerfstudio không đạt chất lượng/tốc độ sau khi đã sửa đúng input/config.

- Tạo adapter riêng cho Gaussian Splatting Lightning hoặc InstantSplat.
- Giữ interface GeometryBackend hiện tại; không đổi API contract chỉ vì engine mới có schema khác.
- Chạy cùng bộ dataset, độ phân giải và giới hạn tài nguyên.
- So sánh registered ratio, reprojection error, thời gian, peak VRAM/RAM, chất lượng novel-view, độ ổn định camera path và khả năng cài đặt.
- Kiểm tra license code, checkpoint, submodule và dependency.
- Chỉ chọn engine thay thế khi có benchmark chứng minh tốt hơn và có quyết định được ghi lại.

### Giai đoạn 9 — GPU local/thuê GPU

Đây là giai đoạn sau, không ghép vào Phase 0/1.

Sau khi render trên một GPU local đã đạt quality gate, định nghĩa interface worker/compute provider để hỗ trợ:
- Local GPU Agent chạy trong máy người dùng/công ty.
- Cloud GPU worker do hệ thống thuê hoặc cấp phát.
- Capability handshake, GPU memory check, queue, heartbeat, cancellation, upload/download artifact và xác thực.
- Phân quyền truy cập file, giới hạn dung lượng, xóa dữ liệu và kiểm soát chi phí.

Không mở cổng Ollama/CUDA hoặc API worker trực tiếp ra Internet. Local Agent phải có authentication, allowlist job, giới hạn quyền, TLS hoặc tunnel an toàn và không thực thi lệnh tùy ý do web client gửi.

## 6. Hợp đồng dữ liệu phải thống nhất

### Camera path

Dùng packages/geometry/camera_path.py làm schema chuẩn. Tối thiểu phải giữ:

- schema_version;
- keyframes có id, image_id khi có, position, rotation_quaternion theo thứ tự xyzw, timestamp_sec;
- focal_length_mm, sensor_width_mm, confidence và locked;
- duration_sec, fps, width, height;
- easing, path_type và tension;
- metadata về nguồn keyframe, baseline, scene extent và quality.

Không lưu Euler angles làm nguồn chính. UI có thể dùng format khác nội bộ nhưng phải chuyển đổi và validate ở biên API.

### Scene/reconstruction

Giữ một Scene record và một representation_uri/version cho mỗi reconstruction có thể tái sử dụng. Kèm diagnostics tối thiểu:

- input asset IDs và hash;
- engine/version/config;
- input image count và registered image count/ratio;
- camera count, sparse point count và reprojection error nếu có;
- geometry confidence, bounds, baseline và các cảnh báo;
- workspace/output URI và trạng thái reconstruction.

Không đánh dấu scene ready nếu chỉ có thư mục output rỗng hoặc lệnh trả exit code 0 nhưng thiếu artifact cần thiết.

### Render job

Mọi render phải có RenderJob và provenance:

- job type, scene/shot/project IDs;
- state, progress, cancellation, start/end time;
- engine version và config hash;
- path validation result;
- output URI, resolution, FPS, duration, file size;
- QC result, stderr/log tail và failure reason.

### Video QC

Trước khi đánh dấu completed, xác nhận file tồn tại, kích thước hợp lý, video giải mã được, FPS/resolution/duration phù hợp và thời lượng lệch trong giới hạn đã quy định. Không coi việc FFmpeg trả exit code 0 là điều kiện QC duy nhất.

## 7. Benchmark và quality gates

Dùng các dataset đã được khai báo trong docs/BENCHMARK_DATASETS.md:

| Dataset ID | Kỳ vọng | Mục tiêu kiểm tra |
|---|---|---|
| exterior-easy-v1 | geometry | overlap tốt, ánh sáng ổn định |
| interior-easy-v1 | geometry | scene nội thất có texture và baseline phù hợp |
| sparse-v1 | fallback | overlap yếu thì không giả geometry |
| single-image-v1 | 2.5d_lite | một ảnh chỉ được tạo chuyển động 2D an toàn |
| disconnected-v1 | transition | ngoại cảnh và nội thất rời nhau không bị gộp sai |

Mỗi lần benchmark phải ghi:
- Git commit và config hash.
- Phiên bản Python, CUDA/PyTorch, COLMAP, Nerfstudio, gsplat và FFmpeg.
- Số ảnh đầu vào, số ảnh đăng ký, registered ratio, camera count, sparse point count, reprojection error.
- Thời gian từng stage, tổng thời gian, peak VRAM/RAM.
- Path score, rejection reasons, thời lượng video, codec, resolution, FPS và file size.
- Artifact URI, log và kết quả QC.

### Các gate bắt buộc

- **Gate A — Unit/API:** toàn bộ test hiện tại và test mới pass.
- **Gate B — Geometry:** exterior-easy-v1 và interior-easy-v1 chạy end-to-end thật trên CUDA; có scene và MP4 xem được.
- **Gate C — Negative cases:** sparse-v1, single-image-v1 và disconnected-v1 fallback đúng policy; không fake 3D.
- **Gate D — Camera path:** schema hợp lệ, quaternion normalized, timestamps tăng, path validation chạy trước render, rejection reasons được trả cho người dùng.
- **Gate E — Render/QC:** MP4 giải mã được; duration/FPS/resolution đúng; job chỉ completed sau QC.
- **Gate F — Reproducibility:** cùng scene, camera path, engine/config và encoder version cho kết quả có thể so sánh; ghi nhận mọi nguồn nondeterminism.
- **Gate G — License:** dependency, model, checkpoint, sample asset và file được copy đều có nguồn/license rõ ràng.

Chỉ khi Gate A–G đạt mới cân nhắc công bố Geometry Mode là tính năng production-ready. Nếu chưa đạt Gate B, tiếp tục giữ fallback an toàn và ghi rõ blocker trong PROJECT_STATUS.md.

## 8. Danh sách file dự kiến thay đổi

Các file hiện có cần ưu tiên kiểm tra/sửa:
- apps/api/app/services/geometry_backend.py
- apps/api/app/services/capabilities.py
- apps/api/app/services/renderer.py
- apps/api/app/workers/render_worker.py
- apps/api/app/schemas/contracts.py
- apps/api/app/models/entities.py
- apps/api/app/api/routes.py
- packages/geometry/camera_path.py
- packages/geometry/keyframes.py
- packages/path_validation/validator.py
- apps/web/app/page.tsx
- docs/PHASE0_CHECKLIST.md
- docs/DEPENDENCY_LICENSE_GATE.md
- docs/BENCHMARK_DATASETS.md
- PROJECT_STATUS.md

Các file mới chỉ được tạo nếu cần và sau khi agent kiểm tra không có chức năng tương đương:
- apps/web/app/components/SceneViewer.tsx
- apps/web/app/components/CameraPathEditor.tsx
- apps/web/app/components/CameraPathTimeline.tsx
- apps/web/lib/cameraPath.ts
- packages/geometry/camera_presets.py
- tests/unit/test_camera_presets.py
- tests/unit/test_camera_path_api.py
- tests/integration/test_geometry_gpu_smoke.py

Đây là kế hoạch đường dẫn đề xuất; không khẳng định các file mới đã tồn tại. Mọi thay đổi database phải có migration hoặc chiến lược tương thích rõ ràng; không giả định JSON schema mới tự động tương thích với database hiện tại.

## 9. License và provenance checklist

Trước khi merge code hoặc phát hành:
- Ghi URL nguồn, commit/tag đã kiểm tra, file/path được lấy ý tưởng hoặc copy.
- Ghi license của repository và license riêng của file/dependency/model/checkpoint.
- Giữ copyright/license notice nếu license yêu cầu.
- Thêm dependency vào manifest đúng hệ sinh thái; pin version đã benchmark.
- Không bundle engine/binary/model nếu chưa xác nhận quyền phân phối.
- Cập nhật docs/DEPENDENCY_LICENSE_GATE.md và docs/EXTERNAL_REPO_SOURCE_MAP.md.
- Đánh dấu rõ code nào là copy/modified, code nào được viết lại độc lập và nguồn tham khảo.
- Đối với engine có license ràng buộc cao, ưu tiên process/API isolation nhưng vẫn phải đánh giá license của việc triển khai và phân phối; tách process không tự động giải quyết mọi nghĩa vụ pháp lý.

## 10. Prompt để giao agent thực hiện đúng quy trình

Giao từng giai đoạn một, không yêu cầu agent ghép tất cả repository trong một lượt.

**Prompt Giai đoạn 0–2:**

    Đọc docs/QUY_TRINH_GHEP_REPO.md, SKILL_CANONICAL.md,
    PROJECT_STATUS.md và docs/ARCHITECTURE.md. Chỉ thực hiện Giai đoạn 0–2.
    Không copy nguyên repository nguồn và không sửa UI ở lượt này.
    Kiểm tra test baseline, môi trường GPU, COLMAP, Nerfstudio và FFmpeg.
    Chạy pipeline geometry hiện có trên một bộ ảnh benchmark được phép sử dụng.
    Không fake kết quả. Ghi log, phiên bản, thời gian, VRAM/RAM và mọi lỗi.
    Chỉ sửa lỗi cần thiết trong adapter hiện có. Chạy test sau mỗi sửa đổi.
    Cập nhật PROJECT_STATUS.md và báo PASS/FAIL từng gate, file đã đổi,
    lệnh đã chạy và blocker còn lại. Dừng nếu pipeline end-to-end chưa đạt.

**Prompt Giai đoạn 3–5:**

    Tiếp tục đọc docs/QUY_TRINH_GHEP_REPO.md. Chỉ thực hiện Giai đoạn 3–5.
    Tận dụng packages/geometry/camera_path.py, keyframes.py,
    packages/scene_grouping/grouper.py và packages/path_validation/validator.py.
    Tham khảo Scene-Gaussian-Splat-Viewer và KIRI-Maker theo đúng đường dẫn
    trong tài liệu; không thay schema canonical. Xây UI timeline/preset,
    nối API và RenderJob hiện tại, viết unit/API/integration tests.
    Không tuyên bố va chạm được kiểm tra tuyệt đối nếu chỉ dùng sparse points.
    Chạy test và báo PASS/FAIL, các file đã đổi và phần chưa hoàn thành.

**Prompt Giai đoạn 6–9:**

    Chỉ bắt đầu khi các gate trước đã pass. Thực hiện orchestration,
    viewer/streaming hoặc GPU provider đúng giai đoạn tương ứng.
    Không ghép nhiều engine hoặc tạo format scene riêng nếu chưa có benchmark
    chứng minh cần thiết. Kiểm tra license cho mọi dependency/model/code.
    Sau mỗi giai đoạn, chạy tests, cập nhật benchmark, PROJECT_STATUS.md,
    docs/DEPENDENCY_LICENSE_GATE.md và docs/EXTERNAL_REPO_SOURCE_MAP.md.
    Không ghi DONE nếu chưa có bằng chứng chạy thực tế.

## 11. Quyết định kiến trúc cuối cùng

Thứ tự ưu tiên được khuyến nghị:

1. **COLMAP + Nerfstudio/Splatfacto:** engine geometry chính; hoàn thiện và benchmark adapter hiện có.
2. **Scene-Gaussian-Splat-Viewer:** tham khảo và tích hợp interaction cho timeline/keyframe vào Next.js.
3. **KIRI-Maker:** tham khảo preset cinematic, chuyển thành keyframe đã kiểm tra geometry.
4. **OOOSplat:** tham khảo pipeline state/progress/cancel/resume, áp dụng vào worker hiện có.
5. **SplatStream:** chỉ làm khi cần streaming/LOD cho scene lớn trên web.
6. **Gaussian Splatting Lightning:** engine đối chứng nếu Nerfstudio không đạt.
7. **InstantSplat:** thử nghiệm riêng cho sparse-view; không tự động thay engine chính.

**Mục tiêu của việc ghép repo không phải tăng số lượng code. Mục tiêu là hoàn thành một đường đi duy nhất, có thể kiểm thử và tái lập:**

    Ảnh gốc bất biến
        → phân tích và grouping
        → COLMAP camera poses + sparse geometry
        → quality gate
        → Nerfstudio/Splatfacto
        → keyframes từ registered views
        → camera path editor
        → path validation
        → ns-render
        → FFmpeg
        → QC
        → MP4 trong storage và link tải từ Web UI

Tài liệu này bổ sung cho docs/EXTERNAL_REPO_SOURCE_MAP.md; khi quyết định tích hợp thay đổi, cập nhật cả hai tài liệu để giữ một nguồn quyết định kiến trúc nhất quán.
