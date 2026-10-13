# IMPLEMENTATION PROMPT — AI-Video Hybrid Auto 3D Studio

> **Use with:** coding agent in VS Code / Claude Code / Codex or comparable repo-aware environment.  
> **Target repository:** https://github.com/hieudang99dd/AI-Video-  
> **Read before implementation:** MASTER_REFACTOR_PLAN.md, SKILL.md, PROJECT_STATUS.md, README.md, HYBRID_AUTO_3D_MODE.md, prototypes/hybrid-auto-3d-studio.html.  
> **Important:** The accompanying HTML is a **clickable product/UI prototype**. It does **not** run real SfM/depth inference/3D or export MP4. Treat it only as a design reference.

## ROLE & OBJECTIVE

You are a senior software architect, browser graphics engineer, 3D reconstruction engineer and testing/security engineer.

**Implement the actual product, not a fake demonstration.**

Build **Hybrid Auto 3D Studio** in the existing AI-Video repo. The user has:
- multiple views of the same infrastructure element (bridge, interchange), potentially suitable for image-based reconstruction;
- scattered images of different stations/locations grouped under the same narrative chapter;
- optionally the original Civil 3D/InfraWorks model exported as FBX or GLB/glTF;
- a company Windows desktop where installation may require administrator authorization.

The user wants a browser UI that lets them create and order groups (Tổng quan, Tuyến chính, Cầu vượt, Nút giao, Thoát nước, ATGT), select images from the PC into each group, request Auto analysis, approve 3D / 2.5D / 2D per subscene, generate an editable narrative storyboard, configure genuine 3D/2.5D/2D cameras and export a **verifiable H.264 MP4**. Local browser capabilities should work without installing a native application; GPU reconstruction/cloud processing must be optional, explicit, permission-checked and truthfully reported.

### Critical distinction

**Group = editorial subject**, **subscene = geometrically coherent capture scene**. E.g. a “Tuyến đường chính” group may include four different highway sections. DO NOT reconstruct all photos as one scene based only on group membership. DO NOT call 2D pan/zoom “3D flythrough”. DO NOT invent new bridge elements, lanes, dimensions, geometric fidelity or QC scores.

## REPO SAFETY / PHASE CONTRACT (MUST DO FIRST)

1. Read current HEAD, branch tree, changes, PR #3 and PR #4, related issues, CI and protected branches.
2. Preserve all P00/P01 security/truthfulness fixes, backups and verified evidence. DO NOT force-push, delete history, modify main directly or overwrite an in-progress worktree.
3. Treat MASTER_REFACTOR_PLAN.md as the canonical source of P00–P11 work and G00–G11 gates. This feature specification adds increments H0–H6; it does not authorize skipping P0 blockers or changing gate definitions.
4. Create a fresh feature branch from the appropriate branch/head with controlled dependency on PR #4, or reconcile PR stack explicitly. Add an issue/ADR indicating the integration strategy.
5. Before modifying code, output a short repository reality check: current app source, API routes, camera/geometry packages, project auth, existing tested 2D output, what is absent, and *why* each new module is needed.
6. Maintain a living task board. Every completed code path needs independent evidence and tests; keep unavailable features labeled NOT_IMPLEMENTED / NOT_RUN.

### Inspected starting points to validate on current HEAD

- apps/web/app/page.tsx — Next.js frontend, project/asset/shot/timeline currently sends fetch requests to backend URL.
- apps/web/package.json — Next 16.3.3, React 19.1.1 on previously inspected branch, Three.js not yet present.
- apps/api/app/api/routes.py — backend routes.
- packages/camera_math, packages/colmap, packages/geometry, packages/path_validation, packages/scene_grouping — inspect actual interfaces.
- tests/unit and tests/integration — extend existing regression coverage.
- index.html, docs/index.html — static demos are not the authoritative Studio and must not claim real GPU/AI/QC results.
- Docs MASTER_REFACTOR_PLAN.md and PROJECT_STATUS.md — evidence-based gates.

## STAGED DELIVERY — IMPLEMENT AND VERIFY IN ORDER

### H0 — Audit & foundation

- Inspect source and git/PR state. Add an ADR for Local Browser vs remote opt-in, truthfulness labels, canonical app.
- Decide monorepo TS packages vs existing Python packages; do not mix languages accidentally.
- Design capability registry: FILE_ACCESS, IMAGE_2D, DEPTH_25D, MODEL_GLB_VIEWER, MODEL_FBX_IMPORT, RECONSTRUCTION_GPU, MP4_H264_BROWSER, MP4_H264_SERVER.
- Each capability is NOT_CHECKED / AVAILABLE / UNAVAILABLE / ERROR, proven by actual probe rather than a configuration boolean.
- Protect P00/P01 negatives: cross-tenant isolation, AI fail-closed, QC not fake, upload limits. If unresolved, do not ship multi-user cloud mode.

**Exit:** architecture note, branch, task board, tests baseline, risk register and blockers.

### H1 — Group Manager / Local Asset Library (IMPLEMENT FIRST)

- Integrate approved prototype layout into authoritative Next.js Studio (real React state and accessible components; do not embed the demo HTML as one iframe).
- Implement create/edit/delete group, reorder groups with drag-and-drop **plus keyboard/up/down alternative**, group descriptions, lock order, image ordering, per-image notes, must-include/optional flags, cross-group reference/move and dedup.
- Let the user select JPG/PNG/WebP from PC, validated by MIME and decode; display real thumbnails; never send file bytes off-machine when Local Only is active.
- Persist drafts in IndexedDB (images with quotas/consent; metadata), versioned JSON or safe project archive export/import; tests across reload, quota failure, deleted file and metadata-only import.
- Clearly distinguish metadata-only export from full project package. Do not persist blob: URLs as durable data.
- Optional FBX/GLB field can be shown as PLANNED initially, no fake viewer.
- Every image remains attached to the user-selected group even after auto-analysis.

**Acceptance:** 5 groups, upload at least 100 test images, reorder/move, reopen project without losing image order; browser network capture confirms no project bytes transferred in Local Only mode; no crashes with invalid files.

### H2 — Real 2D Storyboard + MP4 vertical slice

- Implement deterministic RuleStoryboardEngine driven by ordered groups, selected images and duration target. Call it “Storyboard tự động theo mẫu/quy tắc”, not an LLM unless a real model runs.
- Implement versioned Storyboard/Shot schema, lock/user edits, shot order, camera types KEN_BURNS/PAN/ZOOM, overlays, transition overlap, derived total timeline duration.
- A single shot/camera parameter object drives editor preview AND exported frames.
- Implement an actual local encoder using a supported WebCodecs VideoEncoder codec and real MP4 muxer where browser supports it; else provide explicit unsupported notice or a *consented* remote server render. Never write WebM data to a .mp4 file.
- Frame times are deterministic (n / fps), no setTimeout-based pretend constant-FPS guarantee. Avoid leaking image object URLs, manage memory and cancellation.
- Run independent decode and duration/frame/fps checks on produced MP4. Include screenshot and ffprobe report when backend test environment is available.
- Ensure browser-only mode can be hosted as approved static app without API dependency for H1/H2.

**Acceptance:** input >= 5 genuine user images, create >= 3 shots, render >= 15-second actual H.264 MP4 on supported Chrome/Edge with correct source images, decoded file, observed fps/duration and audio absence correctly recorded.

### H3 — Source-model true 3D from FBX / GLB

- Integrate Three.js GLTFLoader; load sample GLB into interactive viewport and inspect real mesh bounds/materials. Use FBXLoader for supported input; reject corrupt FBX and missing textures honestly. Consider controlled conversion to GLB for durable asset cache; validate converted output.
- Accept FBX + dependencies/texture folder explicitly; design secure mapping of relative texture paths, avoid fetching URLs from arbitrary FBX references without consent.
- Normalize units and axis (Z-up vs Y-up). Preserve geospatial origin, high-precision modelToWorld transform and inverse; render floating origin at local coordinates for large Civil 3D coordinates.
- Set up Orbit, Flyover, Route Follow only against real scene bounds/alignment path. If no alignment data, label a generic 3D flyover/orbit; never claim verified following the CAD centerline.
- Implement unified CameraPathDocument v1 with consistent interpolation/preview/render transforms; validate collision or label UNKNOWN if no collision representation.
- Render actual scene frames and produce at least one true 3D MP4 with parallax from camera movement. Build visibility/texture/scale QA.
- Split large highway models into regions or LOD only based on benchmarking; do not silently decimate away engineering elements.

**Acceptance:** load a reference GLB, orbit gives different occlusions of 3D objects, exported MP4 decodes; documented relative/world transform round-trip. Verify one real Civil 3D/InfraWorks export when licensed/available.

### H4 — Group analyzer, subscenes and optional 2.5D

- Compute usable media evidence: decoded files, duplicate hashes, blur/exposure, image feature matches and geometric inlier verification.
- Build per-group match graph and subscene candidates. Detect disconnected or different-location photos; do not auto-call multiple separate places “one 3D scene”.
- Implement analysis job status and evidence model. Include observed pair matches, registration status, pose degeneration, measurable warnings; do not show invented confidence percentages.
- Integrate depth-estimation ONLY if compatible runtime/backend is actually present. Require observed depth artifact and displacement/hole-filling QA. Restrict parallax amplitude and add visual “2.5D illustrative / not metric”.
- ModeDecisionEngine: source model 3D if loaded and validated; reconstructed 3D only if real scene asset/poses/renderer probe succeed; 2.5D only when depth capability and QA pass; else valid source images get 2D.
- “Force 3D” is a request to attempt/retry, not an authorization to bypass evidence. Engineering accuracy-required shots block unsafe fallback until user confirmation.

**Acceptance:** mismatched-location dataset splits correctly; duplicate screenshots cannot become high-confidence 3D; absence of depth engine results in SOURCE_2D with explicit reason; no fake progress/percentages.

### H5 — Optional real image-to-3D GPU pipeline (do not claim done without GPU runs)

- Design a secure, opt-in remote reconstruction adapter for authorized uploads. Reuse existing packages/colmap and geometry adapters where practical.
- Job: validate incoming set → feature matching → COLMAP sparse pose registration → evaluate residuals / coverage / degeneracy → 3DGS or mesh pipeline → persist **real** scene representation and compatible viewer metadata → scene QA → trial novel-view camera render.
- Record engine version, GPU type/VRAM, source hashes, input count, registered cameras, pose params, artifacts and independent image/video QC.
- If GPU worker absent, mark this capability UNAVAILABLE and keep local group analysis/2D export functioning.
- A 3DGS checkpoint is not automatically a GLB mesh; choose a matching frontend representation or explicit conversion with quality validation.
- Ensure training data license and confidentiality permission; never upload private project files without consent.

**Acceptance:** real consented multi-view infrastructure set produces a renderable scene and a verified novel-view video **or** an explicit measured failure. Separate non-overlap set must fail/fallback. Do not invent PASS if no GPU is available.

### H6 — Hybrid mixed-mode compositor + quality gate

- Combine shots from SOURCE_MODEL_3D, RECONSTRUCTED_3D, DEPTH_25D, SOURCE_2D with consistent resolution, colorspace, fps, safe text areas, audio and transitions.
- Motion Continuity Controller warns about reversals/dolly jumps/unknown spatial continuity and honors user scene order.
- Allow user to inspect asset provenance and effective render mode for every shot before final export. Required technical accuracy must not silently downgrade to 2.5D.
- Build immutable output manifest with input source hashes, camera paths, engine versions, actual backend, fallback reason, AI-inference-performed flag and real QC results. RenderJob only COMPLETED if output exists and independent decode passes.
- Expose one final download link only after verification. Remote jobs require idempotency, lease/heartbeat, cancellation and RBAC.

**Acceptance:** one verified mixed-mode 1080p MP4 with >= 1 true-model 3D shot, >= 1 actual source 2D shot; optional 2.5D and reconstructed 3D included only if actually implemented. Verified camera, audio, title-safe and duration reports.

## API/DATA CONTRACT REQUIREMENTS

Implement/update versioned schemas matching HYBRID_AUTO_3D_MODE.md:
Project, Asset, Group, GroupAsset, Subscene, AnalysisRun, SceneAsset, ModeDecision, Storyboard, Shot, CameraPath, RenderJob, QualityReport, ConsentReceipt, OutputArtifact.

Always separate:
- modeRequested
- modeSuggested
- modeEffective
- capabilityStatus
- evidenceStatus
- fallbackReason
- sourceArtifactSHA256
- worldTransformId / sceneLocalCoordinateSystem

Use typed error/status responses; input validation; per-project auth, resource scopes; safe cancellable jobs, CAS, upload quota. If more than one media group references an image, unlink from one group must not delete original bytes.

Example modes:
- AUTO (user intent only)
- SOURCE_MODEL_3D
- RECONSTRUCTED_3D
- DEPTH_25D
- SOURCE_2D
- UNAVAILABLE

Example evidence statuses:
- NOT_RUN
- INCONCLUSIVE
- VERIFIED
- FAILED

**Never serialize an imaginary field as measured confidence.** No heuristic named “AI” without actual inference, and no pretend user consent.

## UI/UX EXPECTATION

Use prototypes/hybrid-auto-3d-studio.html as visual reference, then implement as real accessible TS/React:
- premium dark technical studio (no unnecessary panels);
- left content groups and group reorder;
- main library and analysis/storyboard tabs;
- right group/asset/shot inspector;
- truthful state badges and explanatory failure messages;
- storyboard cards/timeline with shot duration edits;
- camera viewer for genuine 3D scene and source-image preview for 2D;
- export panel with real capability checks and progress.

Do not keep inert primary action buttons. If not implemented, disable with a visible reason. All controls must be keyboard accessible, responsive and reduce animation for prefers-reduced-motion. No external network uploads in Local Browser, including telemetry of project filenames.

## SECURITY & PRIVACY BLOCKERS

- Company CAD models / images may be confidential; no automatic third-party inference, SaaS uploads, or logs containing sensitive media.
- Strong resource limits and malicious file defenses for image, FBX/GLB, external textures, archives; no path traversal / unsafe shell arguments.
- Project ownership on group/asset/scene/job/download, negative IDOR tests, server-protected token storage; never client-side secrets.
- Preserve original imagery for source fidelity; AI generation cannot certify design specifications.
- Respect company installation/security policy, no admin elevation workarounds.
- Cloud GPU incurs actual cost; product may be free for users only with operator-funded infrastructure/quotas.

## REQUIRED TEST MATRIX

1. Group create/edit/reorder/delete/move asset; multiple group references; IndexedDB reload.
2. Invalid MIME, decompression bomb, oversize, corrupted file; no unhandled exception.
3. Inconsistent/stale metadata, unsupported browser APIs and storage quotas.
4. Real-image file preview, deterministic storyboard, exact timing, independent decoded MP4.
5. Actual GLB render from moved 3D camera, texture and world/local transform roundtrip.
6. Many disconnected photo sites and repeated-crop screenshots explicitly reject 3D.
7. Real SfM dataset and unsuccessful dataset, only if authorized GPU runtime exists.
8. Unauthorized cross-project calls 401/403 on every asset and render endpoint.
9. Re-render invalidation when source, camera, subtitle, model or engine changes.
10. 2D fallback preserves design source; 2.5D restricted where dimensions matter.
11. Chrome/Edge responsive UI, keyboard flow, missing WebCodecs or audio capability.
12. GitHub Actions: existing Python tests, Next.js strict build, backend Docker smoke; GPU tests clearly separate.

## EXECUTION OUTPUT AFTER EACH INCREMENT

At the end of **each** increment H0..H6, return:

- Git branch, commit SHA and draft PR;
- exact list of changed files and architecture reasons;
- acceptance criteria with PASS/FAIL/NOT_RUN;
- test commands, pass counts, CI links;
- real test input provenance, SHA256 and license/authorization;
- artifact paths, ffprobe or browser encode/decode evidence;
- limitations and required environment (WebCodecs/Three.js/GPU worker);
- what remains and whether G00/G01 prerequisites are actually complete;
- rollback and migration notes;
- update PROJECT_STATUS.md with evidence and never silently edit MASTER_REFACTOR_PLAN.md unless an explicit ADR/approved change is needed.

**Do not run ahead and mark H5/GPU/3D as complete on an unavailable workstation.** Stop at the first blocked gate, deliver what is independently provable, state the blocker and continue only with independent workstreams.

## START NOW

1. Inspect HEAD, PR #3/#4, canonical docs and source.
2. Produce 1-page architecture/delta and exact task/issue plan.
3. Start **H1 Group Manager (local-first)** and tests; this is the highest-user-value foundation.
4. Keep H2 as the next vertical slice: real storyboard → verifiable 2D MP4.
5. Only then implement H3+ higher-cost true 3D/reconstruction, respecting existing P00/P01 release blockers.

**Definition of success:** the shipped product actually accepts grouped photos and optional geometry, knows when it *can* and *cannot* build 3D, helps the user approve truthful camera shots, and produces an objectively verified video without quietly changing the engineering project.
