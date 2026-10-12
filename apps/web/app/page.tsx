"use client";
import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Project = { id: string; name: string; status: string; template_name?: string };
type Asset = { id: string; filename: string; analyzed: boolean; width?: number; height?: number };
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
};
type Job = {
  id: string;
  type: string;
  status: string;
  progress: number;
  error?: string | null;
  output_uri?: string | null;
  provenance: Record<string, unknown>;
};

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [assets, setAssets] = useState<Asset[]>([]);
  const [shots, setShots] = useState<Shot[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [shot, setShot] = useState<Shot | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [message, setMessage] = useState("");
  const current = useMemo(() => projects.find((p) => p.id === projectId), [projects, projectId]);

  async function loadProjects() {
    const r = await fetch(`${API}/api/v1/projects`);
    const d = await r.json();
    setProjects(d);
    if (!projectId && d[0]) setProjectId(d[0].id);
  }

  async function loadAssets(pid = projectId) {
    if (!pid) return;
    const r = await fetch(`${API}/api/v1/projects/${pid}/assets`);
    setAssets(await r.json());
  }

  async function loadShots(pid = projectId) {
    if (!pid) return;
    try {
      const r = await fetch(`${API}/api/v1/projects/${pid}`);
      const d = await r.json();
      if (d && d.shots) {
        setShots(d.shots);
        if (d.shots[0] && !shot) setShot(d.shots[0]);
      }
    } catch {}
  }

  useEffect(() => {
    loadProjects().catch(() => {});
  }, []);

  useEffect(() => {
    setSelected([]);
    setShot(null);
    setJob(null);
    setShots([]);
    loadAssets().catch(() => {});
    loadShots().catch(() => {});
  }, [projectId]);

  useEffect(() => {
    if (!job || ["completed", "failed", "cancelled"].includes(job.status)) return;
    const t = setInterval(async () => {
      const r = await fetch(`${API}/api/v1/render-jobs/${job.id}`);
      setJob(await r.json());
    }, 1200);
    return () => clearInterval(t);
  }, [job]);

  async function createProject(fd: FormData) {
    const name = String(fd.get("name") || "").trim();
    if (!name) return;
    const r = await fetch(`${API}/api/v1/projects`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const p = await r.json();
    await loadProjects();
    setProjectId(p.id);
  }

  async function upload(files: FileList | null) {
    if (!files || !projectId) return;
    setMessage("Đang tải ảnh lên...");
    for (const f of Array.from(files)) {
      const fd = new FormData();
      fd.append("file", f);
      const r = await fetch(`${API}/api/v1/projects/${projectId}/assets`, { method: "POST", body: fd });
      if (!r.ok) setMessage(`Upload thất bại: ${await r.text()}`);
    }
    await loadAssets();
    setMessage("Tải ảnh thành công.");
  }

  async function analyze() {
    setMessage("Đang phân tích độ nét & chất lượng ảnh...");
    const r = await fetch(`${API}/api/v1/projects/${projectId}/analyze`, { method: "POST" });
    const d = await r.json();
    setMessage(`Đề xuất: ${d.suggested_mode}`);
    await loadAssets();
  }

  async function applyInfrastructureTemplate() {
    if (!projectId || !assets.length) return;
    setMessage("Đang áp dụng 8 phân cảnh hạ tầng kỹ thuật...");
    const r = await fetch(`${API}/api/v1/projects/${projectId}/apply-template`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ template_id: "infrastructure_8_shots" }),
    });
    if (r.ok) {
      const list = await r.json();
      setShots(list);
      if (list[0]) setShot(list[0]);
      setMessage("Đã tạo Storyboard 8 phân cảnh hạ tầng thành công.");
    } else {
      setMessage(`Lỗi: ${await r.text()}`);
    }
  }

  async function createSingleShot() {
    if (!selected.length) return;
    const r = await fetch(`${API}/api/v1/projects/${projectId}/shots`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: `Shot ${shots.length + 1}`,
        asset_ids: selected,
        duration_sec: 5,
        fps: 30,
        mode: "auto",
        camera_mode: "2D_IMAGE_CAMERA",
        easing: "cinematic",
      }),
    });
    const newShot = await r.json();
    setShots((prev) => [...prev, newShot]);
    setShot(newShot);
  }

  async function previewCurrentShot() {
    if (!shot) return;
    const r = await fetch(`${API}/api/v1/shots/${shot.id}/preview`, { method: "POST" });
    setJob(await r.json());
  }

  async function renderProjectTimeline() {
    if (!projectId) return;
    setMessage("Đang kích hoạt render toàn bộ Timeline...");
    const r = await fetch(`${API}/api/v1/projects/${projectId}/render-timeline`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ resolution: "1080p", fps: 30, include_subtitles: true, include_audio: true }),
    });
    if (r.ok) {
      setJob(await r.json());
      setMessage("Job ghép timeline đã được xếp hàng.");
    } else {
      setMessage(`Lỗi xuất timeline: ${await r.text()}`);
    }
  }

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  return (
    <main>
      <h1>AI-Video: Video Dự Án Hạ Tầng (Civil 3D / InfraWorks)</h1>
      <p className="muted">
        Chuyển đổi thư mục ảnh xuất kỹ thuật thành video giới thiệu có cấu trúc phân cảnh chuẩn, bảo toàn hình học và xuất MP4.
      </p>

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
          {current && (
            <div style={{ marginTop: 8 }}>
              <span className="badge">{current.status}</span>
              {current.template_name && <span className="badge">{current.template_name}</span>}
            </div>
          )}
        </section>

        <section className="card">
          <h2>2. Tải ảnh & Phân tích</h2>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(e) => upload(e.target.files)}
          />
          <button className="secondary" disabled={!assets.length} onClick={analyze}>
            Phân tích hình học & độ nét ({assets.length} ảnh)
          </button>
          <p className="muted">{message}</p>
        </section>
      </div>

      <section className="card">
        <h2>3. Storyboard & Template Hạ Tầng</h2>
        <div style={{ marginBottom: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button onClick={applyInfrastructureTemplate} disabled={!assets.length}>
            ⚡ Áp dụng Template Hạ Tầng (8 Phân Cảnh Chuẩn)
          </button>
          <button className="secondary" disabled={!selected.length} onClick={createSingleShot}>
            + Tạo Shot từ ảnh đã chọn ({selected.length})
          </button>
        </div>

        {shots.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <h3>Danh sách phân cảnh ({shots.length}):</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 10 }}>
              {shots.map((s) => (
                <div
                  key={s.id}
                  onClick={() => setShot(s)}
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    cursor: "pointer",
                    background: shot?.id === s.id ? "#1e293b" : "#0f172a",
                    border: shot?.id === s.id ? "2px solid #38bdf8" : "1px solid #334155",
                  }}
                >
                  <strong>{s.name}</strong>
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    <span className="badge">{s.camera_mode}</span> {s.duration_sec}s
                  </div>
                  {s.overlay_title && (
                    <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>📌 {s.overlay_title}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <h3>Ảnh đã tải lên:</h3>
        {assets.length === 0 ? (
          <p className="muted">Chưa có ảnh nào. Vui lòng tải ảnh từ Civil 3D hoặc InfraWorks.</p>
        ) : (
          assets.map((a) => (
            <label className="asset" key={a.id}>
              <input
                style={{ width: 18, margin: 0 }}
                type="checkbox"
                checked={selected.includes(a.id)}
                onChange={() => toggle(a.id)}
              />
              <div>
                <strong>{a.filename}</strong>
                <div className="muted">
                  {a.analyzed ? `${a.width}×${a.height} · Đã phân tích` : "Chưa phân tích"}
                </div>
              </div>
            </label>
          ))
        )}
      </section>

      <section className="card">
        <h2>4. Render & Xuất bản Video</h2>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
          <button disabled={!shot} onClick={previewCurrentShot}>
            🎬 Render Xem thử Cảnh đang chọn
          </button>
          <button className="secondary" disabled={!shots.length} onClick={renderProjectTimeline}>
            🎞️ Xuất Toàn Bộ Video Dự Án (Timeline MP4)
          </button>
        </div>

        {job && (
          <div style={{ marginTop: 16 }}>
            <p>
              <strong>Loại Job:</strong> {job.type} · <strong>Trạng thái:</strong> {job.status} ·{" "}
              {Math.round(job.progress * 100)}%
            </p>
            <div className="progress">
              <div style={{ width: `${job.progress * 100}%` }} />
            </div>
            {job.error && <pre style={{ color: "#f87171" }}>{job.error}</pre>}
            {job.status === "completed" && (
              <p style={{ marginTop: 12 }}>
                <a
                  href={`${API}/api/v1/render-jobs/${job.id}/download`}
                  style={{
                    display: "inline-block",
                    padding: "10px 18px",
                    background: "#22c55e",
                    color: "#000",
                    fontWeight: "bold",
                    borderRadius: 8,
                    textDecoration: "none",
                  }}
                >
                  ⬇️ Tải Video MP4 Thành Phẩm
                </a>
              </p>
            )}
            <pre>{JSON.stringify(job.provenance, null, 2)}</pre>
          </div>
        )}
      </section>
    </main>
  );
}

