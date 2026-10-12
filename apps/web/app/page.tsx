"use client";
import { useEffect, useMemo, useRef, useState } from "react";

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

  // Studio Player & Timeline States
  const [currentTime, setCurrentTime] = useState(0.0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<"camera" | "cad" | "audio">("camera");
  const [showGrid, setShowGrid] = useState(true);
  const [showSafeZone, setShowSafeZone] = useState(true);
  const [selectedKfIdx, setSelectedKfIdx] = useState<number | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);

  const currentProject = useMemo(() => projects.find((p) => p.id === projectId), [projects, projectId]);
  const shotDuration = selectedShot?.duration_sec || 5.0;

  // Format Timecode: MM:SS:FF (at 30fps)
  function formatTimecode(sec: number, fps = 30) {
    const totalFrames = Math.floor(sec * fps);
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const f = totalFrames % fps;
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${pad(m)}:${pad(s)}:${pad(f)}`;
  }

  async function loadCapabilities() {
    try {
      const res = await fetch(`${API}/api/v1/capabilities`);
      if (res.ok) setCapabilities(await res.json());
    } catch {}
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
    setCurrentTime(0);
    setIsPlaying(false);
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

  // Canvas Studio Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = canvas.width;
    let height = canvas.height;

    // Clear background
    ctx.fillStyle = "#050914";
    ctx.fillRect(0, 0, width, height);

    // Draw Isometric/CAD Grid
    if (showGrid) {
      ctx.strokeStyle = "rgba(30, 58, 95, 0.35)";
      ctx.lineWidth = 1;
      const step = 40;
      for (let x = 0; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Rule of Thirds
      ctx.strokeStyle = "rgba(56, 189, 248, 0.2)";
      ctx.lineWidth = 1.5;
      [width / 3, (width * 2) / 3].forEach((gx) => {
        ctx.beginPath();
        ctx.moveTo(gx, 0);
        ctx.lineTo(gx, height);
        ctx.stroke();
      });
      [(height / 3), (height * 2) / 3].forEach((gy) => {
        ctx.beginPath();
        ctx.moveTo(0, gy);
        ctx.lineTo(width, gy);
        ctx.stroke();
      });
    }

    // Draw Safe Zone Box
    if (showSafeZone) {
      ctx.strokeStyle = "rgba(245, 158, 11, 0.35)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      // 90% Action Safe
      ctx.strokeRect(width * 0.05, height * 0.05, width * 0.9, height * 0.9);
      // 80% Title Safe
      ctx.setLineDash([2, 4]);
      ctx.strokeRect(width * 0.1, height * 0.1, width * 0.8, height * 0.8);
      ctx.setLineDash([]);
    }

    // Draw 3D Camera Trajectory Path on Floor
    const cx = width / 2;
    const cy = height / 2;
    const scale = Math.min(width, height) * 0.3;

    if (cameraPath && cameraPath.keyframes && cameraPath.keyframes.length >= 2) {
      ctx.save();
      // Draw Spline trajectory
      ctx.strokeStyle = "#0ea5e9";
      ctx.lineWidth = 3;
      ctx.beginPath();

      const points = cameraPath.keyframes.map((k) => ({
        x: cx + k.position[0] * scale,
        y: cy + (k.position[2] + 1.5) * scale * 0.8,
        k,
      }));

      points.forEach((pt, idx) => {
        if (idx === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.stroke();

      // Draw Keyframe Diamonds & Frustums
      points.forEach((pt, idx) => {
        const isSel = selectedKfIdx === idx;
        ctx.save();
        ctx.translate(pt.x, pt.y);

        // Frustum pyramid simulation
        ctx.strokeStyle = isSel ? "#f59e0b" : "rgba(56, 189, 248, 0.4)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(-14, -22);
        ctx.lineTo(14, -22);
        ctx.closePath();
        ctx.stroke();

        // Keyframe Diamond
        ctx.rotate(Math.PI / 4);
        ctx.fillStyle = isSel ? "#f59e0b" : "#0284c7";
        ctx.fillRect(-6, -6, 12, 12);
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(-6, -6, 12, 12);
        ctx.restore();

        // Text label
        ctx.font = "bold 10px monospace";
        ctx.fillStyle = isSel ? "#fef08a" : "#cbd5e1";
        ctx.fillText(`KF${idx + 1} (${pt.k.timestamp_sec.toFixed(1)}s)`, pt.x + 10, pt.y - 10);
      });

      // Animated Current Camera Position
      const tNorm = Math.min(1.0, Math.max(0.0, currentTime / (shotDuration || 5.0)));
      // Interpolate position
      const kfA = cameraPath.keyframes[0];
      const kfB = cameraPath.keyframes[cameraPath.keyframes.length - 1];
      const curX = cx + (kfA.position[0] + (kfB.position[0] - kfA.position[0]) * tNorm) * scale;
      const curY = cy + (kfA.position[2] + (kfB.position[2] - kfA.position[2]) * tNorm + 1.5) * scale * 0.8;

      // Active Camera Indicator
      ctx.save();
      ctx.translate(curX, curY);
      ctx.fillStyle = "#ef4444";
      ctx.beginPath();
      ctx.arc(0, 0, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Heading cone
      ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(-24, -40);
      ctx.lineTo(24, -40);
      ctx.closePath();
      ctx.fill();
      ctx.restore();

      ctx.restore();
    } else {
      // Placeholder text
      ctx.font = "14px sans-serif";
      ctx.fillStyle = "#64748b";
      ctx.textAlign = "center";
      ctx.fillText("📷 Chưa tải hoặc chưa chọn Camera Path cho phân cảnh này.", cx, cy);
      ctx.textAlign = "start";
    }

    // Technical banner preview if present
    if (selectedShot?.overlay_title) {
      ctx.save();
      ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
      ctx.strokeStyle = "#0284c7";
      ctx.lineWidth = 1;
      ctx.fillRect(width * 0.1, height * 0.78, width * 0.8, 38);
      ctx.strokeRect(width * 0.1, height * 0.78, width * 0.8, 38);
      ctx.font = "bold 13px sans-serif";
      ctx.fillStyle = "#38bdf8";
      ctx.fillText(selectedShot.overlay_title, width * 0.12, height * 0.82 + 5);
      ctx.restore();
    }
  }, [currentTime, cameraPath, selectedShot, showGrid, showSafeZone, selectedKfIdx, shotDuration]);

  // Playback Animation Frame Loop
  useEffect(() => {
    if (!isPlaying) {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      return;
    }
    lastTimeRef.current = performance.now();
    const loop = (now: number) => {
      const dt = (now - lastTimeRef.current) / 1000;
      lastTimeRef.current = now;
      setCurrentTime((prev) => {
        const next = prev + dt;
        if (next >= shotDuration) {
          setIsPlaying(false);
          return shotDuration;
        }
        return next;
      });
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isPlaying, shotDuration]);

  async function selectShot(shotItem: Shot) {
    setSelectedShot(shotItem);
    setValidationResult(null);
    setLoadingPath(true);
    setCurrentTime(0);
    setIsPlaying(false);
    setSelectedKfIdx(null);
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

  // Camera Presets
  function applyPreset(presetType: "push_in" | "pull_out" | "orbit" | "pan_lr" | "fly_through" | "isometric") {
    if (!selectedShot) return;
    const dur = selectedShot.duration_sec || 5.0;
    let kfs: CameraKeyframe[] = [];

    if (presetType === "push_in") {
      kfs = [
        { id: "kf_1", position: [0, 0, -2.5], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0, 0, -0.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else if (presetType === "pull_out") {
      kfs = [
        { id: "kf_1", position: [0, 0, -0.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0, 0, -2.5], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else if (presetType === "orbit") {
      kfs = [
        { id: "kf_1", position: [-1.6, 0.5, -2.0], rotation_quaternion: [0, 0.22, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0.0, 0.7, -2.3], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur * 0.5, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_3", position: [1.6, 0.5, -2.0], rotation_quaternion: [0, -0.22, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else if (presetType === "pan_lr") {
      kfs = [
        { id: "kf_1", position: [-1.3, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [1.3, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else if (presetType === "fly_through") {
      kfs = [
        { id: "kf_1", position: [0, -0.5, -2.6], rotation_quaternion: [-0.06, 0, 0, 0.998], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 28.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0, 0.9, -0.5], rotation_quaternion: [0.12, 0, 0, 0.992], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
      ];
    } else {
      kfs = [
        { id: "kf_1", position: [-1.2, 1.2, -1.8], rotation_quaternion: [0.15, 0.15, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 50.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
        { id: "kf_2", position: [0.8, 1.2, -1.8], rotation_quaternion: [0.15, -0.15, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 50.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
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
      setMessage(data.ok ? "✅ Quỹ đạo Camera đạt chuẩn hình học." : "⚠️ Quỹ đạo có vi phạm ràng buộc kỹ thuật.");
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
    setSelectedKfIdx(null);
  }

  // Render Job Handlers
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

  function handleScrubberClick(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setCurrentTime(pct * shotDuration);
  }

  return (
    <main>
      <h1>AI-Video: Studio Phân Cảnh Kỹ Thuật (Civil 3D & InfraWorks)</h1>
      <p className="muted">
        Nền tảng biên tập video hạ tầng chuyên nghiệp: mô phỏng camera 2D/3D trực quan, timeline đa track, bộ công cụ quỹ đạo chuẩn điện ảnh và kiểm duyệt chất lượng FFprobe QC.
      </p>

      {/* Capability Matrix Banner */}
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
      </section>

      {/* 1. Project & 2. Assets Quick Bar */}
      <div className="grid">
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
            <div style={{ marginTop: 6 }}>
              <span className="badge">{currentProject.status}</span>
              {currentProject.template_name && <span className="badge green">{currentProject.template_name}</span>}
            </div>
          )}
        </section>

        <section className="card">
          <h2>2. Tải ảnh & Phân tích Hình học</h2>
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
              ⚡ Gom nhóm Scene
            </button>
            <button disabled={!assets.length} onClick={applyInfrastructureTemplate}>
              ⚡ Áp dụng Template 8 Phân Cảnh
            </button>
          </div>
          {message && <p className="muted" style={{ margin: "4px 0 0" }}>{message}</p>}
        </section>
      </div>

      {/* ========================================================
          STUDIO SUITE: TRÌNH BIÊN TẬP PHÂN CẢNH CHUYÊN NGHIỆP
          ======================================================== */}
      <section className="card" style="padding: 12px;">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <h2 style={{ border: "none", margin: 0, padding: 0 }}>
            🎬 Trình Biên Tập Phân Cảnh Chuyên Nghiệp (Studio Suite)
          </h2>
          <div style={{ display: "flex", gap: 6 }}>
            <span className="badge green">{shots.length} Phân Cảnh</span>
            <span className="badge">{selectedShot?.name || "Chưa chọn cảnh"}</span>
          </div>
        </div>

        <div className="studio-layout">
          {/* CỘT TRÁI: VIEWPORT CANVAS & MULTI-TRACK TIMELINE */}
          <div className="studio-viewport-col">
            {/* Viewport Toolbar */}
            <div className="viewport-toolbar">
              <div className="viewport-toolbar-left">
                <span className="timecode-display">
                  {formatTimecode(currentTime)} / {formatTimecode(shotDuration)}
                </span>
                <span style={{ fontSize: 11, color: "#cbd5e1" }}>
                  Tốc độ: <strong>{selectedShot?.fps || 30} FPS</strong>
                </span>
              </div>
              <div className="viewport-toolbar-right">
                <button
                  className={`btn-tool ${showGrid ? "active" : ""}`}
                  onClick={() => setShowGrid(!showGrid)}
                  title="Bật/Tắt Lưới 3x3 và Trắc Địa"
                >
                  📐 Lưới 3x3
                </button>
                <button
                  className={`btn-tool ${showSafeZone ? "active" : ""}`}
                  onClick={() => setShowSafeZone(!showSafeZone)}
                  title="Bật/Tắt Khung An Toàn Tiêu Chuẩn"
                >
                  📺 Khung An Toàn
                </button>
              </div>
            </div>

            {/* Viewport Canvas Screen */}
            <div className="canvas-screen-wrap">
              <canvas ref={canvasRef} className="viewport-canvas" width={960} height={540} />
              <div className="canvas-hud-overlay">
                <div className="canvas-hud-top">
                  <span className="hud-pill">
                    🎯 <strong>{selectedShot?.camera_mode || "2D_IMAGE_CAMERA"}</strong>
                  </span>
                  <span className="hud-pill">
                    🔭 <strong>35.0 mm · FOV 54°</strong>
                  </span>
                </div>
                <div className="canvas-hud-bottom">
                  <span className="hud-pill">
                    🔴 LIVE SIMULATION · 1920×1080
                  </span>
                  {selectedShot?.overlay_title && (
                    <span className="hud-pill" style={{ color: "#38bdf8" }}>
                      📌 {selectedShot.overlay_title}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Transport & Controls Strip */}
            <div className="player-controls-strip">
              <div className="timeline-scrubber-bar" onClick={handleScrubberClick}>
                <div
                  className="timeline-scrubber-progress"
                  style={{ width: `${Math.min(100, (currentTime / (shotDuration || 5)) * 100)}%` }}
                >
                  <div className="timeline-scrubber-thumb" />
                </div>
              </div>

              <div className="ctrl-btn-row">
                <div className="transport-btns">
                  <button className="btn-transport" onClick={() => setCurrentTime(0)} title="Về đầu cảnh">
                    ⏮
                  </button>
                  <button
                    className="btn-transport"
                    onClick={() => setCurrentTime((t) => Math.max(0, t - 1))}
                    title="-1 giây"
                  >
                    ◀ -1s
                  </button>
                  <button
                    className={`btn-transport play`}
                    onClick={() => setIsPlaying(!isPlaying)}
                    title="Phát / Dừng"
                  >
                    {isPlaying ? "⏸ Tạm Dừng" : "▶ Phát"}
                  </button>
                  <button
                    className="btn-transport"
                    onClick={() => setCurrentTime((t) => Math.min(shotDuration, t + 1))}
                    title="+1 giây"
                  >
                    +1s ▶
                  </button>
                  <button
                    className="btn-transport"
                    onClick={() => setCurrentTime(shotDuration)}
                    title="Đến cuối cảnh"
                  >
                    ⏭
                  </button>
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8" }}>
                  Thời lượng: <strong>{shotDuration.toFixed(1)}s</strong> ({Math.round(shotDuration * 30)} frames)
                </div>
              </div>
            </div>

            {/* Multi-Track Timeline */}
            <div className="pro-timeline-container">
              <div className="timeline-header-strip">
                <span>DÒNG THỜI GIAN ĐA TRACK (MULTI-TRACK TIMELINE)</span>
                <span style={{ fontSize: 10.5, color: "#64748b" }}>Nhấp chuột để định vị thời điểm</span>
              </div>

              {/* Ruler */}
              <div className="timeline-ruler">
                {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((sec) => (
                  <div
                    key={sec}
                    className="ruler-tick"
                    style={{ left: `${(sec / (shotDuration || 8)) * 100}%` }}
                  >
                    {sec}s
                  </div>
                ))}
              </div>

              <div className="pro-tracks-area">
                {/* TRACK 1: VIDEO SHOTS */}
                <div className="track-lane">
                  <div className="track-header">🎞️ Video</div>
                  <div className="track-body">
                    {shots.map((s, idx) => (
                      <div
                        key={s.id}
                        className={`shot-clip-item ${selectedShot?.id === s.id ? "active" : ""}`}
                        style={{ flex: s.duration_sec || 5 }}
                        onClick={() => selectShot(s)}
                      >
                        <span>
                          #{idx + 1} {s.name}
                        </span>
                        <span style={{ fontSize: 9.5, opacity: 0.8 }}>{s.duration_sec}s</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* TRACK 2: CAMERA KEYFRAMES */}
                <div className="track-lane">
                  <div className="track-header">📹 Quỹ đạo</div>
                  <div className="track-body" onClick={handleScrubberClick}>
                    {cameraPath?.keyframes.map((kf, idx) => {
                      const posPct = Math.min(100, Math.max(0, (kf.timestamp_sec / (shotDuration || 5)) * 100));
                      return (
                        <div
                          key={idx}
                          className={`kf-diamond-marker ${selectedKfIdx === idx ? "selected" : ""}`}
                          style={{ left: `${posPct}%` }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedKfIdx(idx);
                            setCurrentTime(kf.timestamp_sec);
                          }}
                          title={`Keyframe ${idx + 1} (${kf.timestamp_sec.toFixed(1)}s)`}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* TRACK 3: SUBTITLE / HUD */}
                <div className="track-lane">
                  <div className="track-header">💬 Phụ đề</div>
                  <div className="track-body">
                    <div
                      style={{
                        height: 24,
                        background: "#1e3a5f",
                        borderRadius: 4,
                        padding: "0 8px",
                        display: "flex",
                        alignItems: "center",
                        fontSize: 10.5,
                        color: "#93c5fd",
                        width: "100%",
                      }}
                    >
                      {selectedShot?.overlay_title || selectedShot?.subtitle_text || "Chưa có phụ đề"}
                    </div>
                  </div>
                </div>

                {/* TRACK 4: AUDIO / WAVEFORM */}
                <div className="track-lane">
                  <div className="track-header">🔊 Audio</div>
                  <div className="track-body">
                    <div className="waveform-lane-bars">
                      {Array.from({ length: 48 }).map((_, i) => (
                        <div
                          key={i}
                          className="wf-bar"
                          style={{ height: `${20 + Math.sin(i * 0.5) * 16}%` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* CỘT PHẢI: BẢNG ĐIỀU KHIỂN THUỘC TÍNH (INSPECTOR TABS) */}
          <div className="studio-inspector-col">
            <div className="inspector-tabs-header">
              <button
                className={`tab-btn ${inspectorTab === "camera" ? "active" : ""}`}
                onClick={() => setInspectorTab("camera")}
              >
                📷 Quỹ Đạo
              </button>
              <button
                className={`tab-btn ${inspectorTab === "cad" ? "active" : ""}`}
                onClick={() => setInspectorTab("cad")}
              >
                🏗️ Kỹ Thuật CAD
              </button>
              <button
                className={`tab-btn ${inspectorTab === "audio" ? "active" : ""}`}
                onClick={() => setInspectorTab("audio")}
              >
                🎙️ Thuyết Minh
              </button>
            </div>

            {/* TAB 1: CAMERA & KEYFRAME TRAJECTORY */}
            {inspectorTab === "camera" && (
              <div>
                <h3 style={{ margin: "4px 0" }}>Motion Presets Chuẩn Kỹ Thuật:</h3>
                <div className="preset-grid">
                  <div className="preset-card-item" onClick={() => applyPreset("push_in")}>
                    <div className="preset-title">🎯 Push-In</div>
                    <div className="preset-desc">Tiến gần công trình theo trục Z</div>
                  </div>
                  <div className="preset-card-item" onClick={() => applyPreset("pull_out")}>
                    <div className="preset-title">🔭 Pull-Out</div>
                    <div className="preset-desc">Lùi xa mở rộng đại cảnh</div>
                  </div>
                  <div className="preset-card-item" onClick={() => applyPreset("orbit")}>
                    <div className="preset-title">🔄 Orbit 360</div>
                    <div className="preset-desc">Xoay cung tròn quanh tâm</div>
                  </div>
                  <div className="preset-card-item" onClick={() => applyPreset("pan_lr")}>
                    <div className="preset-title">↔️ Pan Ngang</div>
                    <div className="preset-desc">Trượt ngang trục X giữ góc</div>
                  </div>
                  <div className="preset-card-item" onClick={() => applyPreset("fly_through")}>
                    <div className="preset-title">🦅 Cần Cẩu (Crane)</div>
                    <div className="preset-desc">Nâng cao độ bay bao quát</div>
                  </div>
                  <div className="preset-card-item" onClick={() => applyPreset("isometric")}>
                    <div className="preset-title">📐 Góc Xiên</div>
                    <div className="preset-desc">Trực giao Isometric kỹ thuật</div>
                  </div>
                </div>

                {loadingPath ? (
                  <p className="muted">Đang tải quỹ đạo...</p>
                ) : cameraPath ? (
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
                      <h3 style={{ margin: 0 }}>Danh Sách Keyframes ({cameraPath.keyframes.length}):</h3>
                      <button className="secondary" style={{ padding: "3px 8px", fontSize: 11 }} onClick={addKeyframe}>
                        + Thêm Điểm
                      </button>
                    </div>

                    <div style={{ maxHeight: 200, overflowY: "auto", margin: "6px 0" }}>
                      <table className="kf-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Time (s)</th>
                            <th>X</th>
                            <th>Y</th>
                            <th>Z</th>
                            <th>Focal</th>
                            <th>Xóa</th>
                          </tr>
                        </thead>
                        <tbody>
                          {cameraPath.keyframes.map((kf, idx) => (
                            <tr
                              key={idx}
                              style={{
                                background: selectedKfIdx === idx ? "#172554" : "transparent",
                              }}
                              onClick={() => {
                                setSelectedKfIdx(idx);
                                setCurrentTime(kf.timestamp_sec);
                              }}
                            >
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
                                  style={{ padding: "2px 6px", fontSize: 10 }}
                                  disabled={cameraPath.keyframes.length <= 2}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    removeKeyframe(idx);
                                  }}
                                >
                                  ×
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Validator Box */}
                    {validationResult && (
                      <div className={`validation-box ${validationResult.ok ? "val-valid" : "val-invalid"}`}>
                        <div style={{ fontWeight: 700, display: "flex", justifyContent: "space-between" }}>
                          <span>{validationResult.ok ? "✅ QUỸ ĐẠO HỢP LỆ" : "❌ TỪ CHỐI QUỸ ĐẠO"}</span>
                          <span>Điểm: {(validationResult.score * 100).toFixed(1)}%</span>
                        </div>
                        {validationResult.rejection_reasons.length > 0 && (
                          <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                            {validationResult.rejection_reasons.map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    <div className="btn-row">
                      <button style={{ flex: 1 }} onClick={validateCameraPath}>
                        🔍 Xác Thực Quỹ Đạo
                      </button>
                      <button className="secondary" style={{ flex: 1 }} onClick={saveCameraPath}>
                        💾 Lưu Camera Path
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: 12, background: "#0b101c", borderRadius: 8, fontSize: 12 }}>
                    <p className="muted">Chưa có Camera Path Document.</p>
                    <button onClick={() => applyPreset("push_in")}>Khởi tạo Camera Path Mẫu</button>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: CAD / GIS & SHOT SETTINGS */}
            {inspectorTab === "cad" && selectedShot && (
              <div>
                <label style={{ fontSize: 11, color: "#94a3b8" }}>Tên phân cảnh:</label>
                <input
                  value={selectedShot.name}
                  onChange={(e) => setSelectedShot({ ...selectedShot, name: e.target.value })}
                />

                <label style={{ fontSize: 11, color: "#94a3b8" }}>Thời lượng (giây):</label>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  max="30"
                  value={selectedShot.duration_sec}
                  onChange={(e) => setSelectedShot({ ...selectedShot, duration_sec: Number(e.target.value) })}
                />

                <label style={{ fontSize: 11, color: "#94a3b8" }}>Chế độ Camera (Camera Mode):</label>
                <select
                  value={selectedShot.camera_mode}
                  onChange={(e) => setSelectedShot({ ...selectedShot, camera_mode: e.target.value })}
                >
                  <option value="2D_IMAGE_CAMERA">2D_IMAGE_CAMERA (An toàn bảo toàn hình học CPU)</option>
                  <option value="3D_COLMAP_NERFSTUDIO">3D_COLMAP_NERFSTUDIO (3DGS Splatfacto GPU)</option>
                  <option value="HYBRID_SPLINE_NEURAL">HYBRID_SPLINE_NEURAL (Nội suy Spline)</option>
                </select>

                <label style={{ fontSize: 11, color: "#94a3b8" }}>Banner kỹ thuật / Lý trình:</label>
                <input
                  placeholder="Ví dụ: Km 0+500 - Cầu Vượt Nút Giao Chính"
                  value={selectedShot.overlay_title || ""}
                  onChange={(e) => setSelectedShot({ ...selectedShot, overlay_title: e.target.value })}
                />

                <div className="btn-row" style={{ marginTop: 12 }}>
                  <button className="secondary" style={{ flex: 1 }} onClick={previewCurrentShot}>
                    🎬 Render Xem Thử Shot
                  </button>
                </div>
              </div>
            )}

            {/* TAB 3: AUDIO & NARRATION */}
            {inspectorTab === "audio" && selectedShot && (
              <div>
                <label style={{ fontSize: 11, color: "#94a3b8" }}>Phụ đề kỹ thuật:</label>
                <textarea
                  rows={3}
                  value={selectedShot.subtitle_text || ""}
                  placeholder="Nhập nội dung phụ đề hiển thị đáy màn hình..."
                  onChange={(e) => setSelectedShot({ ...selectedShot, subtitle_text: e.target.value })}
                />

                <label style={{ fontSize: 11, color: "#94a3b8" }}>Lời bình thuyết minh dự án (AI Voiceover):</label>
                <textarea
                  rows={4}
                  value={selectedShot.narration_text || ""}
                  placeholder="Nhập kịch bản thuyết minh kỹ thuật..."
                  onChange={(e) => setSelectedShot({ ...selectedShot, narration_text: e.target.value })}
                />

                <button
                  className="secondary"
                  style={{ width: "100%", marginTop: 8 }}
                  onClick={() => alert("Mô phỏng phát âm thanh thuyết minh AI...")}
                >
                  🔊 Thử Giọng Đọc Mô Phỏng
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 5. Render Timeline & Quality Control */}
      <section className="card">
        <h2>5. Xuất Bản & Kiểm Tra Chất Lượng Video (QC)</h2>
        <div className="btn-row">
          <button className="secondary" disabled={!shots.length} onClick={renderProjectTimeline}>
            🎞️ Xuất Toàn Bộ Video Dự Án (Timeline MP4 1080p)
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
          </div>
        )}
      </section>
    </main>
  );
}
