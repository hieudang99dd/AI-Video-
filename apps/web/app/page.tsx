"use client";
import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Project = { id: string; name: string; status: string; template_name?: string };
type Asset = { id: string; filename: string; analyzed: boolean; width?: number; height?: number; sharpness_score?: number; exposure_score?: number };
type Shot = {
  id: string;
  name: string;
  template_id?: string;
  mode: string;
  camera_mode: string;
  duration_sec: number;
  fps: number;
  overlay_title?: string;
  subtitle_text?: string;
  narration_text?: string;
  camera_path_doc?: Record<string, unknown> | null;
};
type CameraKeyframe = {
  id: string;
  image_id?: string | null;
  position: [number, number, number];
  rotation_quaternion: [number, number, number, number];
  quaternion_order: string;
  timestamp_sec: number;
  focal_length_mm: number;
  sensor_width_mm: number;
  confidence: number;
  locked: boolean;
};
type CameraPathDoc = {
  schema_version: number;
  scene_id?: string | null;
  duration_sec: number;
  fps: number;
  width: number;
  height: number;
  easing: string;
  path_type: string;
  tension: number;
  keyframes: CameraKeyframe[];
  metadata?: Record<string, unknown>;
};
type ValidationResult = {
  ok: boolean;
  score: number;
  rejection_reasons: string[];
  metrics: Record<string, unknown>;
};
type SceneGroup = {
  id: string;
  image_ids: string[];
  size: number;
  confidence: number;
  mode: string;
  edge_count: number;
};
type SceneGroupingResult = {
  groups: SceneGroup[];
  unresolved: string[];
  diagnostics: Record<string, unknown>;
};
type Capabilities = {
  colmap?: { available: boolean };
  cuda?: { available: boolean; device_count?: number; device_name?: string; error?: string };
  nerfstudio?: { train_available: boolean; render_available: boolean };
  geometry?: { available: boolean; train_available: boolean; render_available: boolean; reconstruct_available: boolean };
  ffmpeg?: { available: boolean };
  ffprobe?: { available: boolean };
  fallback_2_5d_lite?: { available: boolean };
};
type Job = {
  id: string;
  type: string;
  status: string;
  progress: number;
  error?: string | null;
  output_uri?: string | null;
  provenance: {
    qc?: {
      container?: string;
      video_codec?: string;
      width?: number;
      height?: number;
      duration_sec?: number;
      fps?: number;
      has_audio?: boolean;
      audio_codec?: string;
      pixel_format?: string;
      valid?: boolean;
      issues?: string[];
    };
    [key: string]: unknown;
  };
};

export default function Home() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [shots, setShots] = useState<Shot[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([]);
  const [selectedShot, setSelectedShot] = useState<Shot | null>(null);
  const [cameraPath, setCameraPath] = useState<CameraPathDoc | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [groupingResult, setGroupingResult] = useState<SceneGroupingResult | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [message, setMessage] = useState("");
  const [loadingPath, setLoadingPath] = useState(false);

  const currentProject = useMemo(() => projects.find((p) => p.id === projectId), [projects, projectId]);

  async function loadCapabilities() {
    try {
      const res = await fetch(`${API}/api/v1/capabilities`);
      if (res.ok) setCapabilities(await res.json());
    } catch {
      // Backend offline fallback
    }
  }

  async function loadProjects() {
    try {
      const r = await fetch(`${API}/api/v1/projects`);
      if (r.ok) {
        const d = await r.json();
        setProjects(d);
        if (!projectId && d[0]) setProjectId(d[0].id);
      }
    } catch {}
  }

  async function loadAssets(pid = projectId) {
    if (!pid) return;
    try {
      const r = await fetch(`${API}/api/v1/projects/${pid}/assets`);
      if (r.ok) setAssets(await r.json());
    } catch {}
  }

  async function loadShots(pid = projectId) {
    if (!pid) return;
    try {
      const r = await fetch(`${API}/api/v1/projects/${pid}`);
      const d = await r.json();
      if (d && d.shots) {
        setShots(d.shots);
        if (d.shots[0] && !selectedShot) selectShot(d.shots[0]);
      }
    } catch {}
  }

  useEffect(() => {
    loadCapabilities();
    loadProjects();
  }, []);

  useEffect(() => {
    setSelectedAssetIds([]);
    setSelectedShot(null);
    setCameraPath(null);
    setValidationResult(null);
    setGroupingResult(null);
    setJob(null);
    setShots([]);
    loadAssets(projectId);
    loadShots(projectId);
  }, [projectId]);

  useEffect(() => {
    if (!job || ["completed", "failed", "cancelled"].includes(job.status)) return;
    const t = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/v1/render-jobs/${job.id}`);
        if (r.ok) setJob(await r.json());
      } catch {}
    }, 1200);
    return () => clearInterval(t);
  }, [job]);

  async function selectShot(shotItem: Shot) {
    setSelectedShot(shotItem);
    setValidationResult(null);
    setLoadingPath(true);
    try {
      const res = await fetch(`${API}/api/v1/shots/${shotItem.id}/camera-path`);
      if (res.ok) {
        const doc = await res.json();
        setCameraPath(doc);
      } else {
        setCameraPath(null);
      }
    } catch {
      setCameraPath(null);
    } finally {
      setLoadingPath(false);
    }
  }

  async function createProject(fd: FormData) {
    const name = String(fd.get("name") || "").trim();
    if (!name) return;
    const r = await fetch(`${API}/api/v1/projects`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (r.ok) {
      const p = await r.json();
      await loadProjects();
      setProjectId(p.id);
    }
  }

  async function uploadFiles(files: FileList | null) {
    if (!files || !projectId) return;
    setMessage("Đang tải ảnh kỹ thuật lên...");
    for (const f of Array.from(files)) {
      const fd = new FormData();
      fd.append("file", f);
      await fetch(`${API}/api/v1/projects/${projectId}/assets`, { method: "POST", body: fd });
    }
    await loadAssets();
    setMessage("Đã tải ảnh lên thành công.");
  }

  async function analyzeImages() {
    if (!projectId) return;
    setMessage("Đang phân tích độ nét & kiểm tra hình học...");
    const r = await fetch(`${API}/api/v1/projects/${projectId}/analyze`, { method: "POST" });
    if (r.ok) {
      const d = await r.json();
      setMessage(`Đã phân tích. Chế độ khuyến nghị: ${d.suggested_mode}`);
      await loadAssets();
    }
  }

  async function groupScenes() {
    if (!projectId) return;
    setMessage("Đang gom nhóm Scene tự động theo liên kết hình học...");
    const r = await fetch(`${API}/api/v1/projects/${projectId}/group-scenes`, { method: "POST" });
    if (r.ok) {
      const res: SceneGroupingResult = await r.json();
      setGroupingResult(res);
      setMessage(`Gom nhóm thành công: ${res.groups.length} nhóm hình học.`);
    } else {
      setMessage(`Lỗi gom nhóm: ${await r.text()}`);
    }
  }

  async function applyInfrastructureTemplate() {
    if (!projectId || !assets.length) return;
    setMessage("Đang áp dụng 8 phân cảnh hạ tầng kỹ thuật chuẩn...");
    const r = await fetch(`${API}/api/v1/projects/${projectId}/apply-template`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ template_id: "infrastructure_8_shots" }),
    });
    if (r.ok) {
      const list = await r.json();
      setShots(list);
      if (list[0]) selectShot(list[0]);
      setMessage("Đã áp dụng Storyboard 8 phân cảnh hạ tầng thành công.");
    }
  }

  async function createCustomShot() {
    if (!selectedAssetIds.length || !projectId) return;
    const r = await fetch(`${API}/api/v1/projects/${projectId}/shots`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: `Shot ${shots.length + 1}`,
        asset_ids: selectedAssetIds,
        duration_sec: 5,
        fps: 30,
        mode: "auto",
        camera_mode: "2D_IMAGE_CAMERA",
        easing: "cinematic",
      }),
    });
    if (r.ok) {
      const newShot = await r.json();
      setShots((prev) => [...prev, newShot]);
      selectShot(newShot);
    }
  }

  // Camera Path Handlers
  function applyPreset(presetType: "push_in" | "orbit" | "pan_lr" | "fly_through") {
    if (!selectedShot) return;
    const dur = selectedShot.duration_sec || 5.0;
    let kfs: CameraKeyframe[] = [];

    if (presetType === "push_in") {
      kfs = [
        { id: "kf_1", position: [0, 0, -2.5], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0, 0, -0.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else if (presetType === "orbit") {
      kfs = [
        { id: "kf_1", position: [-1.5, 0.5, -2.0], rotation_quaternion: [0, 0.2, 0, 0.98], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0.0, 0.7, -2.2], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur * 0.5, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_3", position: [1.5, 0.5, -2.0], rotation_quaternion: [0, -0.2, 0, 0.98], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else if (presetType === "pan_lr") {
      kfs = [
        { id: "kf_1", position: [-1.2, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [1.2, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else {
      kfs = [
        { id: "kf_1", position: [0, -0.4, -2.4], rotation_quaternion: [-0.05, 0, 0, 0.998], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 28.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0, 0.8, -0.6], rotation_quaternion: [0.1, 0, 0, 0.995], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    }

    const newDoc: CameraPathDoc = {
      schema_version: 1,
      duration_sec: dur,
      fps: selectedShot.fps || 30,
      width: 1920,
      height: 1080,
      easing: "cinematic",
      path_type: "catmull_rom",
      tension: 0.5,
      keyframes: kfs,
    };
    setCameraPath(newDoc);
    setValidationResult(null);
  }

  async function validateCameraPath() {
    if (!selectedShot || !cameraPath) return;
    setMessage("Đang xác thực Camera Path theo chuẩn hình học...");
    const res = await fetch(`${API}/api/v1/shots/${selectedShot.id}/camera-path/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cameraPath),
    });
    if (res.ok) {
      const data: ValidationResult = await res.json();
      setValidationResult(data);
      setMessage(data.ok ? "✅ Quỹ đạo Camera hợp lệ." : "⚠️ Quỹ đạo Camera có điểm chưa đạt chuẩn.");
    } else {
      setMessage(`Lỗi xác thực: ${await res.text()}`);
    }
  }

  async function saveCameraPath() {
    if (!selectedShot || !cameraPath) return;
    setMessage("Đang lưu Camera Path lên server...");
    const res = await fetch(`${API}/api/v1/shots/${selectedShot.id}/camera-path`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cameraPath),
    });
    if (res.ok) {
      setMessage("✅ Đã lưu Camera Path thành công.");
      await loadShots();
    } else {
      setMessage(`Lỗi lưu: ${await res.text()}`);
    }
  }

  function updateKeyframe(idx: number, field: string, val: number | string) {
    if (!cameraPath) return;
    const nextKfs = [...cameraPath.keyframes];
    const kf = { ...nextKfs[idx] };
    if (field === "t") kf.timestamp_sec = Number(val);
    else if (field === "x") kf.position = [Number(val), kf.position[1], kf.position[2]];
    else if (field === "y") kf.position = [kf.position[0], Number(val), kf.position[2]];
    else if (field === "z") kf.position = [kf.position[0], kf.position[1], Number(val)];
    else if (field === "focal") kf.focal_length_mm = Number(val);
    nextKfs[idx] = kf;
    setCameraPath({ ...cameraPath, keyframes: nextKfs });
  }

  function addKeyframe() {
    if (!cameraPath) return;
    const last = cameraPath.keyframes[cameraPath.keyframes.length - 1];
    const newKf: CameraKeyframe = {
      id: `kf_${cameraPath.keyframes.length + 1}`,
      position: last ? [last.position[0], last.position[1], last.position[2] + 0.3] : [0, 0, -1],
      rotation_quaternion: [0, 0, 0, 1],
      quaternion_order: "xyzw",
      timestamp_sec: last ? last.timestamp_sec + 1.0 : 1.0,
      focal_length_mm: 35.0,
      sensor_width_mm: 36.0,
      confidence: 1.0,
      locked: false,
    };
    setCameraPath({ ...cameraPath, keyframes: [...cameraPath.keyframes, newKf] });
  }

  function removeKeyframe(idx: number) {
    if (!cameraPath || cameraPath.keyframes.length <= 2) return;
    const nextKfs = cameraPath.keyframes.filter((_, i) => i !== idx);
    setCameraPath({ ...cameraPath, keyframes: nextKfs });
  }

  // Render Handlers
  async function previewCurrentShot() {
    if (!selectedShot) return;
    setMessage("Đang kích hoạt render xem thử cảnh...");
    const r = await fetch(`${API}/api/v1/shots/${selectedShot.id}/preview`, { method: "POST" });
    if (r.ok) {
      setJob(await r.json());
      setMessage("Job xem thử cảnh đã được tạo.");
    }
  }

  async function renderProjectTimeline() {
    if (!projectId) return;
    setMessage("Đang kích hoạt render xuất toàn bộ Timeline...");
    const r = await fetch(`${API}/api/v1/projects/${projectId}/render-timeline`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ resolution: "1080p", fps: 30, include_subtitles: true, include_audio: true }),
    });
    if (r.ok) {
      setJob(await r.json());
      setMessage("Job xuất timeline MP4 đã được xếp hàng.");
    }
  }

  async function cancelCurrentJob() {
    if (!job) return;
    const r = await fetch(`${API}/api/v1/render-jobs/${job.id}/cancel`, { method: "POST" });
    if (r.ok) {
      setJob(await r.json());
      setMessage("Đã gửi yêu cầu hủy render job.");
    }
  }

  function toggleAssetSelection(id: string) {
    setSelectedAssetIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <main>
      <h1>AI-Video: Video Kỹ Thuật Hạ Tầng (Civil 3D & InfraWorks)</h1>
      <p className="muted">
        Chuyển đổi ảnh xuất kỹ thuật thành video giới thiệu có cấu trúc chuẩn, bảo toàn 100% hình học công trình, biên tập Camera Path và xuất MP4 đạt chuẩn QC.
      </p>

      {/* Capability Banner */}
      <section className="cap-banner">
        <div className="cap-header">
          <div className="cap-title">
            <span>⚙️ Trạng Thái Hệ Thống & Môi Trường Tính Toán (Capability Matrix)</span>
          </div>
          <button className="secondary" style={{ padding: "4px 8px", fontSize: 11 }} onClick={loadCapabilities}>
            🔄 Làm mới
          </button>
        </div>
        <div className="cap-badges">
          <span className={`cap-badge ${capabilities?.cuda?.available ? "cap-ok" : "cap-warn"}`}>
            {capabilities?.cuda?.available ? "🟢 CUDA: Sẵn sàng" : "🟡 Chế độ: Safe 2D Motion (CPU Fallback)"}
          </span>
          <span className={`cap-badge ${capabilities?.colmap?.available ? "cap-ok" : "cap-warn"}`}>
            SfM / COLMAP: {capabilities?.colmap?.available ? "Khả dụng" : "Chưa cài đặt"}
          </span>
          <span className={`cap-badge ${capabilities?.nerfstudio?.train_available ? "cap-ok" : "cap-warn"}`}>
            3DGS / Nerfstudio: {capabilities?.nerfstudio?.train_available ? "Sẵn sàng train" : "Chờ GPU"}
          </span>
          <span className={`cap-badge ${capabilities?.ffmpeg?.available ? "cap-ok" : "cap-warn"}`}>
            FFmpeg Encode: {capabilities?.ffmpeg?.available ? "OK" : "Thiếu"}
          </span>
          <span className={`cap-badge ${capabilities?.ffprobe?.available ? "cap-ok" : "cap-info"}`}>
            FFprobe Deep QC: {capabilities?.ffprobe?.available ? "Bật" : "Dung lượng"}
          </span>
        </div>
        {!capabilities?.cuda?.available && (
          <div style={{ fontSize: 11.5, color: "#93c5fd", marginTop: 4 }}>
            ℹ️ <strong>Nguyên tắc an toàn hình học:</strong> Chưa phát hiện GPU NVIDIA CUDA tương thích. Hệ thống kích hoạt an toàn chế độ <code>2D_IMAGE_CAMERA</code> để tránh biến dạng hình học công trình.
          </div>
        )}
      </section>

      {/* Grid: 1. Project & 2. Assets */}
      <div className="grid">
        {/* 1. Project */}
        <section className="card">
          <h2>1. Dự án</h2>
          <form action={createProject}>
            <input name="name" placeholder="Ví dụ: Cao Tốc Bắc - Nam (Đoạn Km0 - Km25)" />
            <button>Tạo dự án</button>
          </form>
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">-- Chọn dự án --</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {currentProject && (
            <div style={{ marginTop: 8 }}>
              <span className="badge">{currentProject.status}</span>
              {currentProject.template_name && <span className="badge green">{currentProject.template_name}</span>}
            </div>
          )}
        </section>

        {/* 2. Upload & Analysis & Grouping */}
        <section className="card">
          <h2>2. Tải ảnh & Nhận diện Hình học</h2>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(e) => uploadFiles(e.target.files)}
          />
          <div className="btn-row">
            <button className="secondary" disabled={!assets.length} onClick={analyzeImages}>
              Phân tích độ nét ({assets.length} ảnh)
            </button>
            <button className="secondary" disabled={!assets.length} onClick={groupScenes}>
              ⚡ Gom nhóm Scene hình học
            </button>
          </div>
          {groupingResult && (
            <div style={{ background: "#0b1120", border: "1px solid #1e293b", padding: 10, borderRadius: 8, fontSize: 12 }}>
              <strong>Kết quả Gom nhóm:</strong> {groupingResult.groups.length} nhóm cảnh | {groupingResult.unresolved.length} ảnh lẻ
            </div>
          )}
          {message && <p className="muted" style={{ marginTop: 6 }}>{message}</p>}
        </section>
      </div>

      {/* 3. Storyboard */}
      <section className="card">
        <h2>3. Storyboard & Phân Cảnh Hạ Tầng</h2>
        <div className="btn-row">
          <button onClick={applyInfrastructureTemplate} disabled={!assets.length}>
            ⚡ Áp dụng Template Hạ Tầng (8 Phân Cảnh Chuẩn)
          </button>
          <button className="secondary" disabled={!selectedAssetIds.length} onClick={createCustomShot}>
            + Tạo Shot từ ảnh đã chọn ({selectedAssetIds.length})
          </button>
        </div>

        {shots.length > 0 && (
          <div>
            <h3>Danh sách phân cảnh ({shots.length}):</h3>
            <div className="shot-grid">
              {shots.map((s) => (
                <div
                  key={s.id}
                  className={`shot-card ${selectedShot?.id === s.id ? "selected" : ""}`}
                  onClick={() => selectShot(s)}
                >
                  <strong style={{ fontSize: 13 }}>{s.name}</strong>
                  <div className="muted" style={{ fontSize: 11.5, marginTop: 4 }}>
                    <span className="badge">{s.camera_mode}</span> {s.duration_sec}s · {s.fps}fps
                  </div>
                  {s.overlay_title && (
                    <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>📌 {s.overlay_title}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Assets check list */}
        <h3>Ảnh trong dự án ({assets.length}):</h3>
        {assets.length === 0 ? (
          <p className="muted">Chưa có ảnh nào. Vui lòng tải ảnh từ Civil 3D hoặc InfraWorks.</p>
        ) : (
          <div style={{ maxHeight: 220, overflowY: "auto" }}>
            {assets.map((a) => (
              <label className="asset" key={a.id}>
                <input
                  style={{ width: 16, margin: 0 }}
                  type="checkbox"
                  checked={selectedAssetIds.includes(a.id)}
                  onChange={() => toggleAssetSelection(a.id)}
                />
                <div>
                  <strong>{a.filename}</strong>
                  <div className="muted">
                    {a.analyzed ? `${a.width}×${a.height} · Độ nét: ${a.sharpness_score?.toFixed(1) ?? "--"}` : "Chưa phân tích"}
                  </div>
                </div>
              </label>
            ))}
          </div>
        )}
      </section>

      {/* 4. Camera Path & Keyframe Editor (MỚI THEO QUY TRÌNH CHUẨN) */}
      {selectedShot && (
        <section className="card">
          <h2>4. Biên tập Camera Path & Xác thực Hình học ({selectedShot.name})</h2>
          <div className="btn-row">
            <span style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8", alignSelf: "center" }}>Presets Quỹ đạo:</span>
            <button className="secondary" onClick={() => applyPreset("push_in")}>🎯 Push-In (Tiến gần)</button>
            <button className="secondary" onClick={() => applyPreset("orbit")}>🔄 Orbit 360 (Quay quanh)</button>
            <button className="secondary" onClick={() => applyPreset("pan_lr")}>↔️ Pan Ngang (Trái - Phải)</button>
            <button className="secondary" onClick={() => applyPreset("fly_through")}>🦅 Bay Cần Cẩu (Crane Up)</button>
          </div>

          {loadingPath ? (
            <p className="muted">Đang tải camera path...</p>
          ) : cameraPath ? (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3>Danh sách Keyframes ({cameraPath.keyframes.length} điểm):</h3>
                <button className="secondary" style={{ padding: "4px 10px", fontSize: 11 }} onClick={addKeyframe}>
                  + Thêm Keyframe
                </button>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table className="kf-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Thời gian (s)</th>
                      <th>Pos X</th>
                      <th>Pos Y</th>
                      <th>Pos Z</th>
                      <th>Tiêu cự (mm)</th>
                      <th>Thao tác</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cameraPath.keyframes.map((kf, idx) => (
                      <tr key={idx}>
                        <td><strong>{idx + 1}</strong></td>
                        <td>
                          <input
                            className="kf-input"
                            type="number"
                            step="0.1"
                            value={kf.timestamp_sec}
                            onChange={(e) => updateKeyframe(idx, "t", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            className="kf-input"
                            type="number"
                            step="0.1"
                            value={kf.position[0]}
                            onChange={(e) => updateKeyframe(idx, "x", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            className="kf-input"
                            type="number"
                            step="0.1"
                            value={kf.position[1]}
                            onChange={(e) => updateKeyframe(idx, "y", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            className="kf-input"
                            type="number"
                            step="0.1"
                            value={kf.position[2]}
                            onChange={(e) => updateKeyframe(idx, "z", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            className="kf-input"
                            type="number"
                            step="1"
                            value={kf.focal_length_mm}
                            onChange={(e) => updateKeyframe(idx, "focal", e.target.value)}
                          />
                        </td>
                        <td>
                          <button
                            className="danger"
                            style={{ padding: "2px 8px", fontSize: 11 }}
                            disabled={cameraPath.keyframes.length <= 2}
                            onClick={() => removeKeyframe(idx)}
                          >
                            Xóa
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Validation Result Box */}
              {validationResult && (
                <div className={`validation-box ${validationResult.ok ? "val-valid" : "val-invalid"}`}>
                  <div style={{ fontWeight: 700, display: "flex", justifyContent: "space-between" }}>
                    <span>{validationResult.ok ? "✅ QUỸ ĐẠO CAMERA HỢP LỆ" : "❌ TỪ CHỐI QUỸ ĐẠO (REJECTED)"}</span>
                    <span>Điểm chất lượng: {(validationResult.score * 100).toFixed(1)}%</span>
                  </div>
                  {validationResult.rejection_reasons.length > 0 && (
                    <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
                      {validationResult.rejection_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              <div className="btn-row">
                <button onClick={validateCameraPath}>🔍 Kiểm tra Quỹ đạo (Validate Path)</button>
                <button className="secondary" onClick={saveCameraPath}>💾 Lưu Camera Path cho Shot</button>
              </div>
            </div>
          ) : (
            <div style={{ padding: 12, background: "#0b101c", borderRadius: 8, fontSize: 12.5 }}>
              <p className="muted">Shot này chưa được khởi tạo Camera Path Document.</p>
              <button onClick={() => applyPreset("push_in")}>Khởi tạo Camera Path mẫu</button>
            </div>
          )}
        </section>
      )}

      {/* 5. Render & Video QC */}
      <section className="card">
        <h2>5. Render, Quản lý Job & Kiểm tra Chất lượng (QC)</h2>
        <div className="btn-row">
          <button disabled={!selectedShot} onClick={previewCurrentShot}>
            🎬 Render Xem thử Cảnh ({selectedShot?.name || "Chưa chọn"})
          </button>
          <button className="secondary" disabled={!shots.length} onClick={renderProjectTimeline}>
            🎞️ Xuất Toàn Bộ Video Dự Án (Timeline MP4)
          </button>
        </div>

        {job && (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <p style={{ margin: 0 }}>
                <strong>Job {job.type}:</strong> <span className="badge">{job.status}</span> ·{" "}
                <strong>{Math.round(job.progress * 100)}%</strong>
              </p>
              {["queued", "processing"].includes(job.status) && (
                <button className="danger" style={{ padding: "4px 10px", fontSize: 11 }} onClick={cancelCurrentJob}>
                  🛑 Hủy Render (Cancel)
                </button>
              )}
            </div>

            <div className="progress">
              <div style={{ width: `${job.progress * 100}%` }} />
            </div>

            {job.error && <pre style={{ color: "#f87171" }}>{job.error}</pre>}

            {/* Deep QC Inspection Grid */}
            {job.status === "completed" && job.provenance?.qc && (
              <div style={{ marginTop: 12 }}>
                <h3 style={{ margin: "8px 0" }}>Báo cáo Kiểm tra Chất lượng (FFprobe Deep QC):</h3>
                <div className="qc-grid">
                  <div className="qc-item">
                    <div className="qc-label">Container</div>
                    <div className="qc-val">{job.provenance.qc.container?.toUpperCase() || "MP4"}</div>
                  </div>
                  <div className="qc-item">
                    <div className="qc-label">Video Codec</div>
                    <div className="qc-val">{job.provenance.qc.video_codec || "H.264"}</div>
                  </div>
                  <div className="qc-item">
                    <div className="qc-label">Resolution</div>
                    <div className="qc-val">{job.provenance.qc.width}×{job.provenance.qc.height}</div>
                  </div>
                  <div className="qc-item">
                    <div className="qc-label">Duration</div>
                    <div className="qc-val">{job.provenance.qc.duration_sec?.toFixed(1)}s</div>
                  </div>
                  <div className="qc-item">
                    <div className="qc-label">Pixel Format</div>
                    <div className="qc-val">{job.provenance.qc.pixel_format || "yuv420p"}</div>
                  </div>
                  <div className="qc-item">
                    <div className="qc-label">Audio Stream</div>
                    <div className="qc-val">{job.provenance.qc.has_audio ? "✅ Có Audio" : "Chỉ Video"}</div>
                  </div>
                </div>
              </div>
            )}

            {job.status === "completed" && (
              <div style={{ marginTop: 14 }}>
                <a
                  href={`${API}/api/v1/render-jobs/${job.id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "10px 18px",
                    background: "#10b981",
                    color: "#022c22",
                    fontWeight: 800,
                    borderRadius: 8,
                    textDecoration: "none",
                  }}
                >
                  ⬇️ Tải Video MP4 Thành Phẩm ({job.type})
                </a>
              </div>
            )}

            <h3 style={{ marginTop: 16 }}>Provenance & Diagnostics:</h3>
            <pre>{JSON.stringify(job.provenance, null, 2)}</pre>
          </div>
        )}
      </section>
    </main>
  );
}
