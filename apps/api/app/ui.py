from pathlib import Path
from fastapi.responses import HTMLResponse

HTML_CONTENT = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI-Video: Video Kỹ Thuật Hạ Tầng (Civil 3D & InfraWorks)</title>
  <style>
    :root { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #070b13; color: #f1f5f9; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 0; }
    main { max-width: 1200px; margin: 0 auto; padding: 28px 20px 80px; }
    h1 { font-size: 28px; margin: 0 0 6px; color: #38bdf8; letter-spacing: -0.3px; }
    h2 { margin-top: 0; font-size: 18px; color: #f8fafc; border-bottom: 1px solid #1e293b; padding-bottom: 8px; }
    h3 { margin: 12px 0 6px; font-size: 14px; color: #cbd5e1; }
    .muted { color: #8492a6; font-size: 13px; margin-bottom: 14px; line-height: 1.5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; margin: 16px 0; }
    input, select, button, textarea { font: inherit; }
    input, select, textarea { width: 100%; padding: 8px 12px; margin: 6px 0 10px; border-radius: 8px; border: 1px solid #334155; background: #090e18; color: #fff; font-size: 13px; }
    input:focus, select:focus, textarea:focus { outline: none; border-color: #38bdf8; }
    button { padding: 8px 14px; border-radius: 8px; border: 0; background: #0ea5e9; color: #041325; cursor: pointer; font-weight: 700; font-size: 13px; transition: all 0.15s; display: inline-flex; align-items: center; gap: 6px; }
    button:hover { background: #38bdf8; }
    button.secondary { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; }
    button.secondary:hover { background: #334155; color: #fff; }
    button.danger { background: #dc2626; color: #fff; }
    button.danger:hover { background: #ef4444; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    .btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
    .asset-item { display: flex; gap: 10px; align-items: center; padding: 8px 0; border-bottom: 1px solid #1e293b; font-size: 12.5px; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 6px; background: #1e293b; font-size: 11px; color: #38bdf8; font-weight: 600; }
    .badge-ok { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #059669; }
    .badge-warn { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid #d97706; }
    .badge-info { background: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid #0284c7; }
    .progress { height: 10px; background: #1e293b; border-radius: 999px; overflow: hidden; margin: 12px 0; }
    .progress-bar { height: 100%; background: linear-gradient(90deg, #0ea5e9, #38bdf8); width: 0%; transition: width 0.3s; }
    pre { white-space: pre-wrap; word-break: break-word; font-size: 11.5px; color: #94a3b8; background: #080d18; padding: 10px; border-radius: 6px; max-height: 200px; overflow-y: auto; }
    a.btn-download { display: inline-flex; align-items: center; gap: 6px; padding: 10px 18px; background: #10b981; color: #022c22; font-weight: bold; border-radius: 8px; text-decoration: none; margin-top: 8px; }
    .storyboard-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; margin-bottom: 14px; }
    .shot-card { padding: 12px; border-radius: 8px; cursor: pointer; background: #0b1120; border: 1px solid #1e293b; transition: all 0.15s; }
    .shot-card:hover { border-color: #38bdf8; }
    .shot-card.selected { border: 2px solid #38bdf8; background: #131f38; }
    .status-msg { padding: 8px 12px; background: #172554; border-radius: 6px; margin: 8px 0; font-size: 12.5px; color: #93c5fd; border: 1px solid #1e40af; }
    .kf-table { width: 100%; border-collapse: collapse; font-size: 12px; margin: 10px 0; }
    .kf-table th { background: #111a2e; padding: 6px 10px; text-align: left; color: #94a3b8; border-bottom: 1px solid #1e293b; }
    .kf-table td { padding: 6px 10px; border-bottom: 1px solid #172033; }
    .kf-input { width: 70px; padding: 4px 6px; margin: 0; font-size: 11.5px; }
    .val-box { border-radius: 8px; padding: 10px 14px; margin: 10px 0; font-size: 12.5px; }
    .val-ok { background: rgba(16, 185, 129, 0.1); border: 1px solid #059669; color: #a7f3d0; }
    .val-fail { background: rgba(239, 68, 68, 0.1); border: 1px solid #dc2626; color: #fca5a5; }
    .qc-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; margin: 10px 0; }
    .qc-item { background: #090e1a; border: 1px solid #1e293b; border-radius: 6px; padding: 8px 10px; }
    .qc-label { font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 700; }
    .qc-val { font-size: 12px; font-weight: 700; color: #f1f5f9; margin-top: 2px; }
  </style>
</head>
<body>
  <main>
    <h1>AI-Video: Video Kỹ Thuật Hạ Tầng (Civil 3D & InfraWorks)</h1>
    <p class="muted">
      Chuyển đổi ảnh xuất kỹ thuật thành video giới thiệu có cấu trúc chuẩn, bảo toàn 100% hình học công trình, biên tập Camera Path và xuất MP4 đạt chuẩn QC.
    </p>

    <!-- Capability Matrix Banner -->
    <section class="card" style="margin-top:0; background:#0b1120; border-color:#1e3a5f;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3 style="margin:0; color:#7dd3fc;">⚙️ Trạng Thái Hệ Thống & Môi Trường Tính Toán (Capability Matrix)</h3>
        <button class="secondary" style="padding:4px 8px; font-size:11px;" onclick="loadCapabilities()">🔄 Làm mới</button>
      </div>
      <div id="capBadges" style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
        <span class="badge badge-warn" id="capCuda">Đang kiểm tra phần cứng...</span>
      </div>
      <div id="capNotice" style="font-size:11.5px; color:#93c5fd; margin-top:6px;"></div>
    </section>

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

      <!-- 2. Tải ảnh & Phân tích & Gom nhóm -->
      <section class="card">
        <h2>2. Tải ảnh & Nhận diện Hình học</h2>
        <input type="file" id="fileInput" accept="image/jpeg,image/png,image/webp" multiple onchange="uploadFiles(this.files)" />
        <div class="btn-row">
          <button class="secondary" id="analyzeBtn" disabled onclick="analyzeImages()">Phân tích độ nét</button>
          <button class="secondary" id="groupBtn" disabled onclick="groupScenes()">⚡ Gom nhóm Scene hình học</button>
        </div>
        <div id="groupResultArea" style="display:none; font-size:12px; padding:8px; background:#0b101c; border-radius:6px; margin-top:6px;"></div>
        <div id="uploadMsg" class="status-msg" style="display:none;"></div>
      </section>
    </div>

    <!-- 3. Storyboard & Template -->
    <section class="card">
      <h2>3. Storyboard & Phân Cảnh Hạ Tầng</h2>
      <div class="btn-row">
        <button id="applyTplBtn" disabled onclick="applyTemplate()">⚡ Áp dụng Template Hạ Tầng (8 Phân Cảnh Chuẩn)</button>
        <button class="secondary" id="createCustomShotBtn" disabled onclick="createCustomShot()">+ Tạo Shot từ ảnh chọn (<span id="selCount">0</span>)</button>
      </div>

      <div id="shotsContainer" style="display:none;">
        <h3>Danh sách các phân cảnh:</h3>
        <div class="storyboard-grid" id="shotsList"></div>
      </div>

      <h3>Ảnh trong dự án:</h3>
      <div id="assetsList"><p class="muted">Chưa có ảnh nào. Vui lòng tải ảnh lên.</p></div>
    </section>

    <!-- 4. Biên tập Camera Path (Mới) -->
    <section class="card" id="cameraPathCard" style="display:none;">
      <h2>4. Biên tập Camera Path & Xác thực Hình học (<span id="selectedShotName">Shot</span>)</h2>
      <div class="btn-row">
        <span style="font-size:12px; font-weight:700; color:#94a3b8; align-self:center;">Presets Quỹ đạo:</span>
        <button class="secondary" onclick="applyPreset('push_in')">🎯 Push-In</button>
        <button class="secondary" onclick="applyPreset('orbit')">🔄 Orbit 360</button>
        <button class="secondary" onclick="applyPreset('pan_lr')">↔️ Pan Ngang</button>
        <button class="secondary" onclick="applyPreset('fly_through')">🦅 Bay Cần Cẩu</button>
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3>Danh sách Keyframes:</h3>
        <button class="secondary" style="padding:4px 10px; font-size:11px;" onclick="addKeyframe()">+ Thêm Keyframe</button>
      </div>

      <div style="overflow-x:auto;">
        <table class="kf-table" id="kfTable">
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
          <tbody id="kfTableBody"></tbody>
        </table>
      </div>

      <div id="validationResultArea"></div>

      <div class="btn-row">
        <button onclick="validateCameraPath()">🔍 Kiểm tra Quỹ đạo (Validate Path)</button>
        <button class="secondary" onclick="saveCameraPath()">💾 Lưu Camera Path cho Shot</button>
      </div>
    </section>

    <!-- 5. Render & Video QC -->
    <section class="card">
      <h2>5. Render, Quản lý Job & Kiểm tra Chất lượng (QC)</h2>
      <div class="btn-row">
        <button id="previewBtn" disabled onclick="previewShot()">🎬 Render Xem thử Cảnh đã chọn</button>
        <button class="secondary" id="timelineBtn" disabled onclick="renderTimeline()">🎞️ Xuất Toàn Bộ Video Dự Án (Timeline MP4)</button>
      </div>

      <div id="jobArea" style="display:none; margin-top: 14px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <p style="margin:0;"><strong id="jobType">Render</strong>: <span id="jobStatus" class="badge">Đang xử lý</span> · <span id="jobPercent">0%</span></p>
          <button class="danger" id="cancelJobBtn" style="padding:4px 10px; font-size:11px; display:none;" onclick="cancelJob()">🛑 Hủy Render (Cancel)</button>
        </div>
        <div class="progress"><div class="progress-bar" id="progressBar"></div></div>
        <div id="jobError" style="color:#f87171; display:none;"></div>
        
        <!-- QC Grid -->
        <div id="qcReportArea" style="display:none;"></div>

        <div id="jobDownloadArea" style="margin: 12px 0;"></div>
        <h3 style="margin-top:12px;">Provenance & Diagnostics:</h3>
        <pre id="jobProvenance"></pre>
      </div>
    </section>
  </main>

  <script>
    let projects = [];
    let currentProjectId = "";
    let assets = [];
    let shots = [];
    let selectedAssetIds = [];
    let selectedShot = null;
    let cameraPath = null;
    let currentJob = null;
    let pollTimer = null;

    async function init() {
      await loadCapabilities();
      await loadProjects();
    }

    async function loadCapabilities() {
      try {
        const res = await fetch("/api/v1/capabilities");
        if (!res.ok) return;
        const c = await res.json();
        const b = document.getElementById("capBadges");
        b.innerHTML = "";
        
        // CUDA
        const cudaOk = c.cuda && c.cuda.available;
        b.innerHTML += `<span class="badge ${cudaOk ? 'badge-ok' : 'badge-warn'}">${cudaOk ? '🟢 CUDA: Sẵn sàng' : '🟡 Chế độ: Safe 2D Motion (CPU Fallback)'}</span>`;
        // COLMAP
        const colmapOk = c.colmap && c.colmap.available;
        b.innerHTML += `<span class="badge ${colmapOk ? 'badge-ok' : 'badge-warn'}">SfM / COLMAP: ${colmapOk ? 'Khả dụng' : 'Chưa cài đặt'}</span>`;
        // Nerfstudio
        const nsTrain = c.nerfstudio && c.nerfstudio.train_available;
        b.innerHTML += `<span class="badge ${nsTrain ? 'badge-ok' : 'badge-warn'}">3DGS: ${nsTrain ? 'Sẵn sàng train' : 'Chờ GPU'}</span>`;
        // FFmpeg
        const ffOk = c.ffmpeg && c.ffmpeg.available;
        b.innerHTML += `<span class="badge ${ffOk ? 'badge-ok' : 'badge-warn'}">FFmpeg: ${ffOk ? 'OK' : 'Thiếu'}</span>`;
        // FFprobe
        const ffpOk = c.ffprobe && c.ffprobe.available;
        b.innerHTML += `<span class="badge ${ffpOk ? 'badge-ok' : 'badge-info'}">FFprobe Deep QC: ${ffpOk ? 'Bật' : 'Dung lượng'}</span>`;

        const notice = document.getElementById("capNotice");
        if (!cudaOk) {
          notice.innerHTML = "ℹ️ <strong>Nguyên tắc an toàn hình học:</strong> Chưa phát hiện GPU NVIDIA CUDA. Hệ thống kích hoạt an toàn chế độ <code>2D_IMAGE_CAMERA</code> để giữ trọn hình học công trình.";
        } else {
          notice.innerHTML = "🟢 Hệ thống có GPU CUDA. Tái dựng 3DGS và Camera Spline được hỗ trợ đầy đủ.";
        }
      } catch (e) {
        console.warn("Lỗi load capabilities:", e);
      }
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
      cameraPath = null;
      document.getElementById("cameraPathCard").style.display = "none";
      updateSelCount();
      if (!currentProjectId) {
        document.getElementById("assetsList").innerHTML = '<p class="muted">Chưa chọn dự án.</p>';
        document.getElementById("shotsContainer").style.display = "none";
        document.getElementById("projStatusArea").innerHTML = "";
        return;
      }
      const cur = projects.find(p => p.id === currentProjectId);
      if (cur) {
        document.getElementById("projStatusArea").innerHTML = `<span class="badge">${cur.status}</span>${cur.template_name ? '<span class="badge badge-info">' + cur.template_name + '</span>' : ''}`;
      }
      await loadAssets();
      await loadShots();
    }

    async function loadAssets() {
      if (!currentProjectId) return;
      const res = await fetch(`/api/v1/projects/${currentProjectId}/assets`);
      assets = await res.json();
      document.getElementById("analyzeBtn").disabled = (assets.length === 0);
      document.getElementById("groupBtn").disabled = (assets.length === 0);
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
          <input type="checkbox" style="width:16px;margin:0;" value="${a.id}" onchange="toggleAsset('${a.id}', this.checked)" />
          <div>
            <strong>${a.filename}</strong>
            <div class="muted">${a.analyzed ? `${a.width}×${a.height} · Độ nét: ${a.sharpness_score ? a.sharpness_score.toFixed(1) : '--'}` : 'Chưa phân tích'}</div>
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
      showMsg("Đang phân tích độ nét & kiểm tra hình học...");
      const res = await fetch(`/api/v1/projects/${currentProjectId}/analyze`, { method: "POST" });
      const data = await res.json();
      showMsg(`Đã phân tích. Chế độ đề xuất: ${data.suggested_mode}`);
      await loadAssets();
    }

    async function groupScenes() {
      if (!currentProjectId) return;
      showMsg("Đang gom nhóm Scene hình học tự động...");
      const res = await fetch(`/api/v1/projects/${currentProjectId}/group-scenes`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const area = document.getElementById("groupResultArea");
        area.style.display = "block";
        area.innerHTML = `<strong>Kết quả gom nhóm:</strong> ${data.groups.length} nhóm cảnh hình học | ${data.unresolved.length} ảnh lẻ`;
        showMsg("Đã hoàn tất gom nhóm Scene theo liên kết hình học.");
      } else {
        showMsg("Lỗi gom nhóm: " + (await res.text()));
      }
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
          <div style="font-size:11.5px;margin:4px 0;">
            <span class="badge">${s.camera_mode || '2D_IMAGE_CAMERA'}</span> ${s.duration_sec}s
          </div>
          ${s.overlay_title ? `<div style="font-size:11px;color:#94a3b8;">📌 ${s.overlay_title}</div>` : ''}
        `;
        list.appendChild(card);
      });
      if (!selectedShot && shots[0]) selectShot(shots[0]);
    }

    async function selectShot(s) {
      selectedShot = s;
      document.getElementById("selectedShotName").textContent = s.name;
      document.getElementById("previewBtn").disabled = false;
      document.querySelectorAll(".shot-card").forEach(c => c.classList.remove("selected"));
      document.getElementById("cameraPathCard").style.display = "block";
      document.getElementById("validationResultArea").innerHTML = "";
      
      // Load Camera Path for Shot
      try {
        const res = await fetch(`/api/v1/shots/${s.id}/camera-path`);
        if (res.ok) {
          cameraPath = await res.json();
        } else {
          cameraPath = null;
        }
      } catch (e) {
        cameraPath = null;
      }
      renderKeyframesTable();
      loadShots();
    }

    function renderKeyframesTable() {
      const tbody = document.getElementById("kfTableBody");
      tbody.innerHTML = "";
      if (!cameraPath || !cameraPath.keyframes || !cameraPath.keyframes.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="color:#94a3b8;text-align:center;">Chưa có Keyframe nào. Chọn một Preset ở trên để tạo quỹ đạo.</td></tr>';
        return;
      }
      cameraPath.keyframes.forEach((kf, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${idx + 1}</strong></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.timestamp_sec}" onchange="updateKf(${idx}, 't', this.value)" /></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.position[0]}" onchange="updateKf(${idx}, 'x', this.value)" /></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.position[1]}" onchange="updateKf(${idx}, 'y', this.value)" /></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.position[2]}" onchange="updateKf(${idx}, 'z', this.value)" /></td>
          <td><input class="kf-input" type="number" step="1" value="${kf.focal_length_mm}" onchange="updateKf(${idx}, 'focal', this.value)" /></td>
          <td><button class="danger" style="padding:2px 8px;font-size:11px;" ${cameraPath.keyframes.length <= 2 ? 'disabled' : ''} onclick="removeKf(${idx})">Xóa</button></td>
        `;
        tbody.appendChild(tr);
      });
    }

    function updateKf(idx, field, val) {
      if (!cameraPath) return;
      const kf = cameraPath.keyframes[idx];
      if (field === 't') kf.timestamp_sec = parseFloat(val);
      else if (field === 'x') kf.position[0] = parseFloat(val);
      else if (field === 'y') kf.position[1] = parseFloat(val);
      else if (field === 'z') kf.position[2] = parseFloat(val);
      else if (field === 'focal') kf.focal_length_mm = parseFloat(val);
    }

    function addKeyframe() {
      if (!cameraPath) {
        applyPreset('push_in');
        return;
      }
      const last = cameraPath.keyframes[cameraPath.keyframes.length - 1];
      const newKf = {
        id: `kf_${cameraPath.keyframes.length + 1}`,
        position: last ? [last.position[0], last.position[1], last.position[2] + 0.3] : [0, 0, -1],
        rotation_quaternion: [0, 0, 0, 1],
        quaternion_order: "xyzw",
        timestamp_sec: last ? last.timestamp_sec + 1.0 : 1.0,
        focal_length_mm: 35.0,
        sensor_width_mm: 36.0,
        confidence: 1.0,
        locked: false
      };
      cameraPath.keyframes.push(newKf);
      renderKeyframesTable();
    }

    function removeKf(idx) {
      if (!cameraPath || cameraPath.keyframes.length <= 2) return;
      cameraPath.keyframes.splice(idx, 1);
      renderKeyframesTable();
    }

    function applyPreset(presetType) {
      if (!selectedShot) return;
      const dur = selectedShot.duration_sec || 5.0;
      let kfs = [];
      if (presetType === "push_in") {
        kfs = [
          { id: "kf_1", position: [0, 0, -2.5], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0, 0, -0.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else if (presetType === "orbit") {
        kfs = [
          { id: "kf_1", position: [-1.5, 0.5, -2.0], rotation_quaternion: [0, 0.2, 0, 0.98], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0.0, 0.7, -2.2], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur * 0.5, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_3", position: [1.5, 0.5, -2.0], rotation_quaternion: [0, -0.2, 0, 0.98], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else if (presetType === "pan_lr") {
        kfs = [
          { id: "kf_1", position: [-1.2, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [1.2, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else {
        kfs = [
          { id: "kf_1", position: [0, -0.4, -2.4], rotation_quaternion: [-0.05, 0, 0, 0.998], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 28.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0, 0.8, -0.6], rotation_quaternion: [0.1, 0, 0, 0.995], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      }
      cameraPath = {
        schema_version: 1,
        duration_sec: dur,
        fps: selectedShot.fps || 30,
        width: 1920,
        height: 1080,
        easing: "cinematic",
        path_type: "catmull_rom",
        tension: 0.5,
        keyframes: kfs
      };
      renderKeyframesTable();
      document.getElementById("validationResultArea").innerHTML = "";
    }

    async function validateCameraPath() {
      if (!selectedShot || !cameraPath) return;
      showMsg("Đang kiểm tra tính liên tục và gia tốc của Camera Path...");
      const res = await fetch(`/api/v1/shots/${selectedShot.id}/camera-path/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cameraPath)
      });
      if (res.ok) {
        const val = await res.json();
        const area = document.getElementById("validationResultArea");
        area.innerHTML = `
          <div class="val-box ${val.ok ? 'val-ok' : 'val-fail'}">
            <div style="font-weight:700; display:flex; justify-content:space-between;">
              <span>${val.ok ? '✅ QUỸ ĐẠO CAMERA HỢP LỆ' : '❌ TỪ CHỐI QUỸ ĐẠO (REJECTED)'}</span>
              <span>Điểm đánh giá: ${(val.score * 100).toFixed(1)}%</span>
            </div>
            ${val.rejection_reasons.length > 0 ? '<ul style="margin:6px 0 0 16px;padding:0;">' + val.rejection_reasons.map(r => `<li>${r}</li>`).join('') + '</ul>' : ''}
          </div>
        `;
        showMsg(val.ok ? "✅ Quỹ đạo Camera đạt chuẩn hình học." : "⚠️ Quỹ đạo có vi phạm ràng buộc kỹ thuật.");
      } else {
        showMsg("Lỗi xác thực: " + (await res.text()));
      }
    }

    async function saveCameraPath() {
      if (!selectedShot || !cameraPath) return;
      showMsg("Đang lưu Camera Path lên server...");
      const res = await fetch(`/api/v1/shots/${selectedShot.id}/camera-path`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cameraPath)
      });
      if (res.ok) {
        showMsg("✅ Đã lưu Camera Path thành công.");
        await loadShots();
      } else {
        showMsg("Lỗi khi lưu Camera Path: " + (await res.text()));
      }
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
      showMsg("Đang kích hoạt render xem thử...");
      const res = await fetch(`/api/v1/shots/${selectedShot.id}/preview`, { method: "POST" });
      currentJob = await res.json();
      startPollingJob();
    }

    async function renderTimeline() {
      if (!currentProjectId) return;
      showMsg("Đang kích hoạt render timeline MP4...");
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

    async function cancelJob() {
      if (!currentJob) return;
      const res = await fetch(`/api/v1/render-jobs/${currentJob.id}/cancel`, { method: "POST" });
      if (res.ok) {
        currentJob = await res.json();
        showMsg("Đã gửi yêu cầu hủy render job.");
        updateJobUI();
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
      
      const cancelBtn = document.getElementById("cancelJobBtn");
      cancelBtn.style.display = ["queued", "processing"].includes(currentJob.status) ? "inline-flex" : "none";

      const errBox = document.getElementById("jobError");
      if (currentJob.error) {
        errBox.style.display = "block";
        errBox.textContent = currentJob.error;
      } else {
        errBox.style.display = "none";
      }

      // QC Inspector
      const qcArea = document.getElementById("qcReportArea");
      if (currentJob.status === "completed" && currentJob.provenance && currentJob.provenance.qc) {
        const qc = currentJob.provenance.qc;
        qcArea.style.display = "block";
        qcArea.innerHTML = `
          <h3 style="margin:8px 0;">Báo cáo Kiểm tra Chất lượng (FFprobe Deep QC):</h3>
          <div class="qc-grid">
            <div class="qc-item"><div class="qc-label">Container</div><div class="qc-val">${(qc.container || 'mp4').toUpperCase()}</div></div>
            <div class="qc-item"><div class="qc-label">Video Codec</div><div class="qc-val">${qc.video_codec || 'H.264'}</div></div>
            <div class="qc-item"><div class="qc-label">Resolution</div><div class="qc-val">${qc.width || 1920}×${qc.height || 1080}</div></div>
            <div class="qc-item"><div class="qc-label">Duration</div><div class="qc-val">${qc.duration_sec ? qc.duration_sec.toFixed(1) + 's' : '--'}</div></div>
            <div class="qc-item"><div class="qc-label">Pixel Format</div><div class="qc-val">${qc.pixel_format || 'yuv420p'}</div></div>
            <div class="qc-item"><div class="qc-label">Audio Stream</div><div class="qc-val">${qc.has_audio ? '✅ Có Audio' : 'Chỉ Video'}</div></div>
          </div>
        `;
      } else {
        qcArea.style.display = "none";
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


def get_ui_html() -> HTMLResponse:
    # Always prioritize up-to-date HTML_CONTENT embedded template
    # or fallback to local files if present and non-empty.
    return HTMLResponse(content=HTML_CONTENT, status_code=200)
