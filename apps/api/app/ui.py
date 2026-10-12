from fastapi.responses import HTMLResponse

HTML_CONTENT = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI-Video: Video Dự Án Hạ Tầng (Civil 3D / InfraWorks)</title>
  <style>
    :root { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0d10; color: #f5f7fa; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 0; }
    main { max-width: 1160px; margin: 0 auto; padding: 36px 20px 80px; }
    h1 { font-size: 32px; margin: 0 0 8px; color: #38bdf8; }
    h2 { margin-top: 0; font-size: 20px; color: #f8fafc; border-bottom: 1px solid #252c35; padding-bottom: 8px; }
    h3 { margin: 12px 0 8px; font-size: 15px; color: #cbd5e1; }
    .muted { color: #9da7b3; font-size: 14px; margin-bottom: 16px; line-height: 1.5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    .card { background: #14181e; border: 1px solid #252c35; border-radius: 14px; padding: 20px; margin: 18px 0; }
    input, select, button { font: inherit; }
    input, select { width: 100%; padding: 10px 12px; margin: 6px 0 12px; border-radius: 8px; border: 1px solid #333d49; background: #0f1318; color: #fff; }
    button { padding: 10px 16px; border-radius: 8px; border: 0; background: #38bdf8; color: #0f172a; cursor: pointer; font-weight: 700; transition: opacity 0.2s; }
    button:hover { opacity: 0.9; }
    button.secondary { background: #29313b; color: #f8fafc; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    .btn-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
    .asset-item { display: flex; gap: 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid #202731; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 999px; background: #242b34; margin-right: 6px; font-size: 12px; color: #38bdf8; }
    .badge-mode { background: #1e3a5f; color: #7dd3fc; }
    .progress { height: 10px; background: #242b34; border-radius: 999px; overflow: hidden; margin: 12px 0; }
    .progress-bar { height: 100%; background: #38bdf8; width: 0%; transition: width 0.3s; }
    pre { white-space: pre-wrap; word-break: break-word; font-size: 12px; color: #c6d0db; background: #0c0f14; padding: 12px; border-radius: 8px; max-height: 240px; overflow-y: auto; }
    a.btn-download { display: inline-block; padding: 12px 20px; background: #22c55e; color: #052e16; font-weight: bold; border-radius: 8px; text-decoration: none; margin-top: 8px; }
    .storyboard-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-bottom: 16px; }
    .shot-card { padding: 12px; border-radius: 8px; cursor: pointer; background: #0f172a; border: 1px solid #334155; transition: border-color 0.2s; }
    .shot-card.selected { border: 2px solid #38bdf8; background: #1e293b; }
    .status-msg { padding: 8px 12px; background: #1a222d; border-radius: 6px; margin: 8px 0; font-size: 13px; color: #93c5fd; }
  </style>
</head>
<body>
  <main>
    <h1>AI-Video: Video Giới Thiệu Dự Án Hạ Tầng</h1>
    <p class="muted">
      Chuyển đổi thư mục ảnh xuất kỹ thuật từ <strong>Autodesk Civil 3D</strong> và <strong>InfraWorks</strong> thành video giới thiệu có cấu trúc phân cảnh rõ ràng, bảo toàn 100% hình học công trình và xuất file MP4 H.264.
    </p>

    <div class="grid">
      <!-- 1. Dự án -->
      <section class="card">
        <h2>1. Dự án</h2>
        <div style="display:flex; gap:8px;">
          <input id="projNameInput" placeholder="Tên dự án (vd: Cao Tốc Bắc - Nam Km0-Km25)" />
          <button style="white-space:nowrap;" onclick="createProject()">Tạo dự án</button>
        </div>
        <select id="projSelect" onchange="onProjectChange()">
          <option value="">-- Chọn dự án --</option>
        </select>
        <div id="projStatusArea"></div>
      </section>

      <!-- 2. Tải ảnh & Phân tích -->
      <section class="card">
        <h2>2. Tải ảnh & Phân tích chất lượng</h2>
        <input type="file" id="fileInput" accept="image/jpeg,image/png,image/webp" multiple onchange="uploadFiles(this.files)" />
        <div class="btn-row">
          <button class="secondary" id="analyzeBtn" disabled onclick="analyzeImages()">Phân tích độ nét & kiểm tra hình học</button>
        </div>
        <div id="uploadMsg" class="status-msg" style="display:none;"></div>
      </section>
    </div>

    <!-- 3. Storyboard & Template -->
    <section class="card">
      <h2>3. Storyboard & 8 Phân Cảnh Chuẩn</h2>
      <div class="btn-row">
        <button id="applyTplBtn" disabled onclick="applyTemplate()">⚡ Áp dụng Template Hạ Tầng (8 Phân Cảnh Chuẩn)</button>
        <button class="secondary" id="createCustomShotBtn" disabled onclick="createCustomShot()">+ Tạo Shot từ ảnh chọn (<span id="selCount">0</span>)</button>
      </div>

      <div id="shotsContainer" style="display:none;">
        <h3>Danh sách các phân cảnh:</h3>
        <div class="storyboard-grid" id="shotsList"></div>
      </div>

      <h3>Ảnh trong dự án:</h3>
      <div id="assetsList"><p class="muted">Chưa có ảnh nào. Vui lòng chọn hoặc tải ảnh lên.</p></div>
    </section>

    <!-- 4. Render & Xuất bản Video -->
    <section class="card">
      <h2>4. Render & Xuất bản Video</h2>
      <div class="btn-row">
        <button id="previewBtn" disabled onclick="previewShot()">🎬 Render Xem thử Cảnh đã chọn</button>
        <button class="secondary" id="timelineBtn" disabled onclick="renderTimeline()">🎞️ Xuất Toàn Bộ Video Dự Án (Timeline MP4)</button>
      </div>

      <div id="jobArea" style="display:none; margin-top: 16px;">
        <p><strong id="jobType">Render</strong>: <span id="jobStatus">Đang xử lý</span> · <span id="jobPercent">0%</span></p>
        <div class="progress"><div class="progress-bar" id="progressBar"></div></div>
        <div id="jobError" style="color:#f87171; display:none;"></div>
        <div id="jobDownloadArea" style="margin: 14px 0;"></div>
        <pre id="jobProvenance"></pre>
      </div>
    </section>
  </main>

  <script>
    const API = "";
    let projects = [];
    let currentProjectId = "";
    let assets = [];
    let shots = [];
    let selectedAssetIds = [];
    let selectedShot = null;
    let currentJob = null;
    let pollTimer = null;

    async function init() {
      await loadProjects();
    }

    async function loadProjects() {
      try {
        const res = await fetch("/api/v1/projects");
        projects = await res.json();
        const sel = document.getElementById("projSelect");
        sel.innerHTML = '<option value="">-- Chọn dự án --</option>';
        projects.forEach(p => {
          const opt = document.createElement("option");
          opt.value = p.id;
          opt.textContent = p.name;
          sel.appendChild(opt);
        });
        if (!currentProjectId && projects[0]) {
          currentProjectId = projects[0].id;
          sel.value = currentProjectId;
          onProjectChange();
        }
      } catch (e) { console.error(e); }
    }

    async function createProject() {
      const nameInput = document.getElementById("projNameInput");
      const name = nameInput.value.trim();
      if (!name) return;
      const res = await fetch("/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      });
      const p = await res.json();
      nameInput.value = "";
      await loadProjects();
      currentProjectId = p.id;
      document.getElementById("projSelect").value = currentProjectId;
      onProjectChange();
    }

    async function onProjectChange() {
      currentProjectId = document.getElementById("projSelect").value;
      selectedAssetIds = [];
      selectedShot = null;
      updateSelCount();
      if (!currentProjectId) {
        document.getElementById("assetsList").innerHTML = '<p class="muted">Chưa chọn dự án.</p>';
        document.getElementById("shotsContainer").style.display = "none";
        document.getElementById("projStatusArea").innerHTML = "";
        return;
      }
      const cur = projects.find(p => p.id === currentProjectId);
      if (cur) {
        document.getElementById("projStatusArea").innerHTML = `<span class="badge">${cur.status}</span>${cur.template_name ? '<span class="badge badge-mode">' + cur.template_name + '</span>' : ''}`;
      }
      await loadAssets();
      await loadShots();
    }

    async function loadAssets() {
      if (!currentProjectId) return;
      const res = await fetch(`/api/v1/projects/${currentProjectId}/assets`);
      assets = await res.json();
      document.getElementById("analyzeBtn").disabled = (assets.length === 0);
      document.getElementById("applyTplBtn").disabled = (assets.length === 0);
      const container = document.getElementById("assetsList");
      if (!assets.length) {
        container.innerHTML = '<p class="muted">Chưa có ảnh nào. Vui lòng tải ảnh lên.</p>';
        return;
      }
      container.innerHTML = "";
      assets.forEach(a => {
        const div = document.createElement("div");
        div.className = "asset-item";
        div.innerHTML = `
          <input type="checkbox" style="width:18px;margin:0;" value="${a.id}" onchange="toggleAsset('${a.id}', this.checked)" />
          <div>
            <strong>${a.filename}</strong>
            <div class="muted">${a.analyzed ? `${a.width}×${a.height} · Đã phân tích` : 'Chưa phân tích'}</div>
          </div>
        `;
        container.appendChild(div);
      });
    }

    function toggleAsset(id, checked) {
      if (checked) {
        if (!selectedAssetIds.includes(id)) selectedAssetIds.push(id);
      } else {
        selectedAssetIds = selectedAssetIds.filter(x => x !== id);
      }
      updateSelCount();
    }

    function updateSelCount() {
      document.getElementById("selCount").textContent = selectedAssetIds.length;
      document.getElementById("createCustomShotBtn").disabled = (selectedAssetIds.length === 0);
    }

    async function uploadFiles(files) {
      if (!files || !currentProjectId) return;
      showMsg("Đang tải tệp lên...");
      for (const f of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", f);
        await fetch(`/api/v1/projects/${currentProjectId}/assets`, { method: "POST", body: fd });
      }
      showMsg("Đã tải lên toàn bộ ảnh thành công.");
      await loadAssets();
    }

    async function analyzeImages() {
      if (!currentProjectId) return;
      showMsg("Đang phân tích độ nét & trắc địa...");
      const res = await fetch(`/api/v1/projects/${currentProjectId}/analyze`, { method: "POST" });
      const data = await res.json();
      showMsg(`Đã phân tích. Chế độ đề xuất: ${data.suggested_mode}`);
      await loadAssets();
    }

    async function loadShots() {
      if (!currentProjectId) return;
      const res = await fetch(`/api/v1/projects/${currentProjectId}`);
      const data = await res.json();
      shots = data.shots || [];
      const cont = document.getElementById("shotsContainer");
      const list = document.getElementById("shotsList");
      document.getElementById("timelineBtn").disabled = (shots.length === 0);
      if (!shots.length) {
        cont.style.display = "none";
        return;
      }
      cont.style.display = "block";
      list.innerHTML = "";
      shots.forEach(s => {
        const card = document.createElement("div");
        card.className = "shot-card" + (selectedShot && selectedShot.id === s.id ? " selected" : "");
        card.onclick = () => selectShot(s);
        card.innerHTML = `
          <strong>${s.name}</strong>
          <div style="font-size:12px;margin:4px 0;">
            <span class="badge">${s.camera_mode || '2D_IMAGE_CAMERA'}</span> ${s.duration_sec}s
          </div>
          ${s.overlay_title ? `<div style="font-size:11px;color:#94a3b8;">📌 ${s.overlay_title}</div>` : ''}
        `;
        list.appendChild(card);
      });
      if (!selectedShot && shots[0]) selectShot(shots[0]);
    }

    function selectShot(s) {
      selectedShot = s;
      document.getElementById("previewBtn").disabled = false;
      document.querySelectorAll(".shot-card").forEach(c => c.classList.remove("selected"));
      loadShots();
    }

    async function applyTemplate() {
      if (!currentProjectId || !assets.length) return;
      showMsg("Đang tạo Storyboard 8 phân cảnh hạ tầng...");
      const res = await fetch(`/api/v1/projects/${currentProjectId}/apply-template`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: "infrastructure_8_shots" })
      });
      if (res.ok) {
        showMsg("Đã áp dụng 8 phân cảnh chuẩn thành công.");
        await loadShots();
      } else {
        showMsg("Lỗi khi áp dụng template: " + (await res.text()));
      }
    }

    async function createCustomShot() {
      if (!selectedAssetIds.length || !currentProjectId) return;
      const res = await fetch(`/api/v1/projects/${currentProjectId}/shots`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `Shot ${shots.length + 1}`,
          asset_ids: selectedAssetIds,
          duration_sec: 5,
          fps: 30,
          mode: "auto",
          camera_mode: "2D_IMAGE_CAMERA",
          easing: "cinematic"
        })
      });
      if (res.ok) {
        showMsg("Đã tạo Shot mới.");
        await loadShots();
      }
    }

    async function previewShot() {
      if (!selectedShot) return;
      const res = await fetch(`/api/v1/shots/${selectedShot.id}/preview`, { method: "POST" });
      currentJob = await res.json();
      startPollingJob();
    }

    async function renderTimeline() {
      if (!currentProjectId) return;
      const res = await fetch(`/api/v1/projects/${currentProjectId}/render-timeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution: "1080p", fps: 30, include_subtitles: true, include_audio: true })
      });
      if (res.ok) {
        currentJob = await res.json();
        startPollingJob();
      } else {
        showMsg("Lỗi khi render timeline: " + (await res.text()));
      }
    }

    function startPollingJob() {
      if (pollTimer) clearInterval(pollTimer);
      document.getElementById("jobArea").style.display = "block";
      updateJobUI();
      pollTimer = setInterval(async () => {
        if (!currentJob) return;
        const res = await fetch(`/api/v1/render-jobs/${currentJob.id}`);
        currentJob = await res.json();
        updateJobUI();
        if (["completed", "failed", "cancelled"].includes(currentJob.status)) {
          clearInterval(pollTimer);
        }
      }, 1200);
    }

    function updateJobUI() {
      if (!currentJob) return;
      document.getElementById("jobType").textContent = currentJob.type === "timeline" ? "Xuất Timeline Dự Án" : "Xem thử Cảnh";
      document.getElementById("jobStatus").textContent = currentJob.status;
      const pct = Math.round(currentJob.progress * 100);
      document.getElementById("jobPercent").textContent = `${pct}%`;
      document.getElementById("progressBar").style.width = `${pct}%`;
      const errBox = document.getElementById("jobError");
      if (currentJob.error) {
        errBox.style.display = "block";
        errBox.textContent = currentJob.error;
      } else {
        errBox.style.display = "none";
      }
      const dlArea = document.getElementById("jobDownloadArea");
      if (currentJob.status === "completed" && currentJob.output_uri) {
        dlArea.innerHTML = `<a class="btn-download" href="/api/v1/render-jobs/${currentJob.id}/download" target="_blank">⬇️ Tải Video MP4 Thành Phẩm (${currentJob.type})</a>`;
      } else {
        dlArea.innerHTML = "";
      }
      document.getElementById("jobProvenance").textContent = JSON.stringify(currentJob.provenance || {}, null, 2);
    }

    function showMsg(text) {
      const box = document.getElementById("uploadMsg");
      box.style.display = "block";
      box.textContent = text;
    }

    window.onload = init;
  </script>
</body>
</html>
"""


from pathlib import Path


def get_ui_html() -> HTMLResponse:
    candidates = [
        Path(__file__).resolve().parents[3] / "index.html",
        Path(__file__).resolve().parents[3] / "docs" / "index.html",
        Path("index.html"),
    ]
    for p in candidates:
        if p.is_file():
            try:
                return HTMLResponse(content=p.read_text(encoding="utf-8"), status_code=200)
            except Exception:
                pass
    return HTMLResponse(content=HTML_CONTENT, status_code=200)
