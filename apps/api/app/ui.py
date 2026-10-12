from pathlib import Path
from fastapi.responses import HTMLResponse

HTML_CONTENT = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI-Video: Studio Phân Cảnh Kỹ Thuật (Civil 3D & InfraWorks)</title>
  <style>
    :root {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #070b12;
      color: #f1f5f9;
      --bg-main: #070b12;
      --bg-card: #0c1220;
      --border: #1a263c;
      --primary: #0ea5e9;
      --primary-hover: #38bdf8;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-red: #ef4444;
    }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 0; background: var(--bg-main); color: #f1f5f9; font-size: 13px; }
    main { max-width: 1440px; margin: 0 auto; padding: 20px 24px 80px; }

    h1 { font-size: 26px; margin: 0 0 6px; color: #38bdf8; letter-spacing: -0.4px; font-weight: 800; }
    h2 { margin-top: 0; font-size: 16px; color: #f8fafc; border-bottom: 1px solid var(--border); padding-bottom: 8px; font-weight: 700; }
    h3 { margin: 10px 0 6px; font-size: 13px; color: #cbd5e1; font-weight: 700; }
    .muted { color: #8492a6; font-size: 12.5px; margin-bottom: 12px; line-height: 1.5; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
    .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin: 16px 0; }

    input, select, button, textarea { font: inherit; }
    input, select, textarea {
      width: 100%; padding: 7px 11px; margin: 5px 0 9px; border-radius: 7px;
      border: 1px solid #24344d; background: #080d17; color: #fff; font-size: 12.5px;
    }
    input:focus, select:focus, textarea:focus { outline: none; border-color: var(--primary); }

    button {
      padding: 7px 13px; border-radius: 7px; border: 0; background: var(--primary);
      color: #041325; cursor: pointer; font-weight: 700; font-size: 12.5px;
      transition: all 0.15s; display: inline-flex; align-items: center; gap: 6px; justify-content: center;
    }
    button:hover { background: var(--primary-hover); transform: translateY(-1px); }
    button.secondary { background: #131e33; color: #e2e8f0; border: 1px solid #24344d; }
    button.secondary:hover { background: #1c2b47; color: #fff; }
    button.danger { background: #dc2626; color: #fff; }
    button.danger:hover { background: #ef4444; }
    button:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

    .btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
    .asset-item { display: flex; gap: 10px; align-items: center; padding: 7px 0; border-bottom: 1px solid #141f33; font-size: 12px; }
    .badge { display: inline-block; padding: 2px 7px; border-radius: 5px; background: #131e33; color: #38bdf8; font-size: 11px; font-weight: 600; border: 1px solid #20314f; }
    .badge-ok { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid #059669; }
    .badge-warn { background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid #d97706; }
    .badge-info { background: rgba(14, 165, 233, 0.12); color: #38bdf8; border: 1px solid #0284c7; }

    .status-msg { padding: 8px 12px; background: #172554; border-radius: 6px; margin: 8px 0; font-size: 12.5px; color: #93c5fd; border: 1px solid #1e40af; }

    /* STUDIO LAYOUT */
    .studio-layout {
      display: grid;
      grid-template-columns: 1fr 380px;
      gap: 16px;
      background: #090e18;
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      margin: 14px 0;
    }
    @media (max-width: 1080px) {
      .studio-layout { grid-template-columns: 1fr; }
    }

    .studio-viewport-col {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #070b13;
      border-right: 1px solid var(--border);
    }

    .viewport-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      color: #94a3b8;
    }
    .timecode-display {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      font-weight: 800;
      color: #38bdf8;
      background: #040810;
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px solid #1a2a44;
      letter-spacing: 0.5px;
    }
    .btn-tool {
      padding: 4px 8px; font-size: 11px; background: #111a2d; color: #94a3b8;
      border: 1px solid #1f2e47; border-radius: 5px; cursor: pointer;
    }
    .btn-tool.active { background: #172554; color: #38bdf8; border-color: #0284c7; }

    .canvas-screen-wrap {
      position: relative;
      width: 100%;
      aspect-ratio: 16/9;
      background: #000;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid #1e2c44;
      box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    }
    .viewport-canvas { width: 100%; height: 100%; display: block; }

    .canvas-hud-overlay {
      position: absolute; inset: 0; pointer-events: none;
      display: flex; flex-direction: column; justify-content: space-between; padding: 12px;
    }
    .hud-pill {
      background: rgba(4, 8, 16, 0.75); backdrop-filter: blur(6px);
      border: 1px solid rgba(56, 189, 248, 0.3); color: #e2e8f0;
      font-size: 10.5px; font-weight: 700; padding: 3px 8px; border-radius: 4px;
    }

    /* CONTROLS STRIP */
    .player-controls-strip {
      display: flex; flex-direction: column; gap: 8px; background: #0a101d;
      padding: 10px 14px; border-radius: 8px; border: 1px solid #18253b;
    }
    .timeline-scrubber-bar {
      position: relative; height: 8px; background: #152238; border-radius: 4px; cursor: pointer;
    }
    .timeline-scrubber-progress {
      height: 100%; background: linear-gradient(90deg, #0284c7, #38bdf8); border-radius: 4px; width: 0%;
      position: relative;
    }
    .timeline-scrubber-thumb {
      position: absolute; right: -5px; top: -4px; width: 16px; height: 16px;
      background: #fff; border: 2px solid #0284c7; border-radius: 50%;
      box-shadow: 0 0 8px rgba(14, 165, 233, 0.6);
    }
    .ctrl-btn-row { display: flex; justify-content: space-between; align-items: center; }
    .btn-transport {
      background: #111a2c; border: 1px solid #1f2e47; color: #cbd5e1;
      padding: 5px 10px; border-radius: 6px; font-size: 13px; cursor: pointer;
    }
    .btn-transport:hover { background: #1c2b47; color: #fff; }
    .btn-transport.play { background: #0284c7; color: #fff; border-color: #0ea5e9; font-weight: 700; }

    /* MULTI TRACK TIMELINE */
    .pro-timeline-container {
      background: #060a12; border: 1px solid #17243a; border-radius: 8px; overflow: hidden; margin-top: 4px;
    }
    .timeline-header-strip {
      display: flex; justify-content: space-between; align-items: center; padding: 6px 12px;
      background: #090f1c; border-bottom: 1px solid #17243a; font-size: 11px; font-weight: 700; color: #94a3b8;
    }
    .timeline-ruler {
      height: 20px; background: #080d19; border-bottom: 1px solid #141e30; display: flex;
      align-items: center; padding-left: 90px; font-size: 10px; color: #64748b; position: relative; font-family: monospace;
    }
    .ruler-tick { position: absolute; border-left: 1px solid #17243a; padding-left: 4px; }

    .track-lane { display: flex; height: 36px; border-bottom: 1px solid #121c2e; align-items: center; position: relative; }
    .track-header {
      width: 90px; min-width: 90px; height: 100%; background: #0a1120; border-right: 1px solid #152238;
      display: flex; align-items: center; gap: 6px; padding: 0 8px; font-size: 11px; font-weight: 700; color: #94a3b8;
    }
    .track-body { flex: 1; height: 100%; background: rgba(10, 16, 29, 0.5); position: relative; display: flex; align-items: center; overflow: hidden; }

    .shot-clip-item {
      height: 28px; background: #172554; border: 1px solid #1e40af; border-radius: 4px; margin: 0 2px; padding: 0 8px;
      display: flex; align-items: center; justify-content: space-between; font-size: 11px; font-weight: 700; color: #bfdbfe;
      cursor: pointer; white-space: nowrap; transition: all 0.15s;
    }
    .shot-clip-item.active { background: #1e3a8a; border: 2px solid #38bdf8; color: #fff; }

    .kf-diamond-marker {
      position: absolute; top: 50%; transform: translate(-50%, -50%) rotate(45deg); width: 12px; height: 12px;
      background: #0ea5e9; border: 1.5px solid #fff; box-shadow: 0 0 6px #0284c7; cursor: pointer; z-index: 5;
    }
    .kf-diamond-marker.selected { background: #f59e0b; border-color: #fff; }

    .wf-bar { width: 2px; background: #10b981; border-radius: 1px; margin-right: 2px; opacity: 0.8; }

    /* INSPECTOR TABS */
    .studio-inspector-col {
      padding: 16px; display: flex; flex-direction: column; gap: 12px; background: #0a0f1c; overflow-y: auto; max-height: 850px;
    }
    .inspector-tabs-header { display: flex; border-bottom: 1px solid #1a2a44; gap: 4px; }
    .tab-btn {
      padding: 7px 12px; font-size: 11.5px; font-weight: 700; color: #8492a6; background: transparent; border: none;
      border-bottom: 2px solid transparent; cursor: pointer;
    }
    .tab-btn.active { color: #38bdf8; border-bottom: 2px solid #0ea5e9; }

    .preset-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin: 8px 0; }
    .preset-card-item {
      background: #0d1526; border: 1px solid #1a2942; border-radius: 8px; padding: 8px 10px; cursor: pointer; transition: all 0.15s;
    }
    .preset-card-item:hover { border-color: #0284c7; background: #131e36; }
    .preset-title { font-size: 11.5px; font-weight: 700; color: #fff; }
    .preset-desc { font-size: 10px; color: #8492a6; margin-top: 2px; }

    .kf-table { width: 100%; border-collapse: collapse; font-size: 11.5px; margin: 8px 0; }
    .kf-table th { background: #0e172a; padding: 5px 6px; text-align: left; color: #94a3b8; border-bottom: 1px solid #1e2c44; font-size: 10.5px; }
    .kf-table td { padding: 4px 6px; border-bottom: 1px solid #141f33; }
    .kf-input { width: 56px; padding: 3px 5px; margin: 0; font-size: 11px; }

    .val-box { border-radius: 8px; padding: 10px 12px; margin: 8px 0; font-size: 12px; }
    .val-ok { background: rgba(16, 185, 129, 0.1); border: 1px solid #059669; color: #a7f3d0; }
    .val-fail { background: rgba(239, 68, 68, 0.1); border: 1px solid #dc2626; color: #fca5a5; }

    .qc-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; margin: 10px 0; }
    .qc-item { background: #080d18; border: 1px solid #18263e; border-radius: 6px; padding: 8px 10px; }
    .qc-label { font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 700; }
    .qc-val { font-size: 12px; font-weight: 700; color: #f1f5f9; margin-top: 2px; }

    .progress { height: 8px; background: #131e33; border-radius: 999px; overflow: hidden; margin: 10px 0; }
    .progress-bar { height: 100%; background: linear-gradient(90deg, #0ea5e9, #38bdf8); width: 0%; transition: width 0.3s; }
    pre { white-space: pre-wrap; word-break: break-word; font-size: 11px; color: #94a3b8; background: #070b14; padding: 10px; border-radius: 6px; max-height: 200px; overflow-y: auto; }
    a.btn-download { display: inline-flex; align-items: center; gap: 6px; padding: 10px 18px; background: #10b981; color: #022c22; font-weight: bold; border-radius: 8px; text-decoration: none; margin-top: 8px; }
  </style>
</head>
<body>
  <main>
    <h1>AI-Video: Studio Phân Cảnh Kỹ Thuật (Civil 3D & InfraWorks)</h1>
    <p class="muted">
      Nền tảng biên tập video hạ tầng chuyên nghiệp: mô phỏng camera 2D/3D trực quan, timeline đa track, bộ công cụ quỹ đạo chuẩn điện ảnh và kiểm duyệt chất lượng FFprobe QC.
    </p>

    <!-- Capability Matrix Banner -->
    <section class="card" style="margin-top:0; background:#0b1120; border-color:#1e3a5f;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3 style="margin:0; color:#7dd3fc;">⚙️ Trạng Thái Hệ Thống & Môi Trường Tính Toán (Capability Matrix)</h3>
        <button class="secondary" style="padding:4px 8px; font-size:11px;" onclick="loadCapabilities()">🔄 Làm mới</button>
      </div>
      <div id="capBadges" style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
        <span class="badge badge-warn">Đang kiểm tra phần cứng...</span>
      </div>
    </section>

    <!-- 1. Project & 2. Assets -->
    <div class="grid">
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

      <section class="card">
        <h2>2. Tải ảnh & Phân tích Hình học</h2>
        <input type="file" id="fileInput" accept="image/jpeg,image/png,image/webp" multiple onchange="uploadFiles(this.files)" />
        <div class="btn-row">
          <button class="secondary" id="analyzeBtn" disabled onclick="analyzeImages()">Phân tích độ nét</button>
          <button class="secondary" id="groupBtn" disabled onclick="groupScenes()">⚡ Gom nhóm Scene</button>
          <button id="applyTplBtn" disabled onclick="applyTemplate()">⚡ Áp dụng Template 8 Phân Cảnh</button>
        </div>
        <div id="uploadMsg" class="status-msg" style="display:none;"></div>
      </section>
    </div>

    <!-- ========================================================
        STUDIO SUITE: TRÌNH BIÊN TẬP PHÂN CẢNH CHUYÊN NGHIỆP
        ======================================================== -->
    <section class="card" style="padding:14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <h2 style="border:none; margin:0; padding:0;">
          🎬 Trình Biên Tập Phân Cảnh Chuyên Nghiệp (Studio Suite)
        </h2>
        <div style="display:flex; gap:6px;">
          <span class="badge badge-ok" id="shotCountBadge">0 Phân Cảnh</span>
          <span class="badge" id="activeShotBadge">Chưa chọn cảnh</span>
        </div>
      </div>

      <div class="studio-layout">
        <!-- CỘT TRÁI: VIEWPORT CANVAS & MULTI-TRACK TIMELINE -->
        <div class="studio-viewport-col">
          <!-- Toolbar -->
          <div class="viewport-toolbar">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="timecode-display" id="timecodeDisplay">00:00:00 / 00:05:00</span>
              <span style="font-size:11px; color:#cbd5e1;">Tốc độ: <strong id="fpsDisplay">30 FPS</strong></span>
            </div>
            <div style="display:flex; gap:6px;">
              <button class="btn-tool active" id="btnToggleGrid" onclick="toggleGrid()">📐 Lưới 3x3</button>
              <button class="btn-tool active" id="btnToggleSafe" onclick="toggleSafeZone()">📺 Khung An Toàn</button>
            </div>
          </div>

          <!-- Canvas Viewport -->
          <div class="canvas-screen-wrap">
            <canvas id="studioCanvas" class="viewport-canvas" width="960" height="540"></canvas>
            <div class="canvas-hud-overlay">
              <div style="display:flex; justify-content:space-between;">
                <span class="hud-pill" id="hudCameraMode">🎯 2D_IMAGE_CAMERA</span>
                <span class="hud-pill">🔭 35.0 mm · FOV 54°</span>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span class="hud-pill">🔴 LIVE SIMULATION · 1920×1080</span>
                <span class="hud-pill" id="hudTitle" style="color:#38bdf8; display:none;">📌 Tiêu đề</span>
              </div>
            </div>
          </div>

          <!-- Transport Scrubber -->
          <div class="player-controls-strip">
            <div class="timeline-scrubber-bar" id="scrubberBar" onclick="handleScrub(event)">
              <div class="timeline-scrubber-progress" id="scrubberProgress">
                <div class="timeline-scrubber-thumb"></div>
              </div>
            </div>

            <div class="ctrl-btn-row">
              <div style="display:flex; gap:6px;">
                <button class="btn-transport" onclick="seekTime(0)">⏮</button>
                <button class="btn-transport" onclick="seekTime(currentTime - 1)">◀ -1s</button>
                <button class="btn-transport play" id="playBtn" onclick="togglePlay()">▶ Phát</button>
                <button class="btn-transport" onclick="seekTime(currentTime + 1)">+1s ▶</button>
                <button class="btn-transport" onclick="seekTime(currentShotDuration)">⏭</button>
              </div>
              <div style="font-size:11px; color:#94a3b8;">
                Thời lượng: <strong id="durText">5.0s</strong> (150 frames)
              </div>
            </div>
          </div>

          <!-- Multi-Track Timeline -->
          <div class="pro-timeline-container">
            <div class="timeline-header-strip">
              <span>DÒNG THỜI GIAN ĐA TRACK (MULTI-TRACK TIMELINE)</span>
              <span style="font-size:10px; color:#64748b;">Nhấp chuột để định vị</span>
            </div>

            <div class="timeline-ruler" id="timelineRuler"></div>

            <div class="track-lane">
              <div class="track-header">🎞️ Video</div>
              <div class="track-body" id="trackVideoClips"></div>
            </div>

            <div class="track-lane">
              <div class="track-header">📹 Quỹ đạo</div>
              <div class="track-body" id="trackKeyframes" onclick="handleScrub(event)"></div>
            </div>

            <div class="track-lane">
              <div class="track-header">💬 Phụ đề</div>
              <div class="track-body" id="trackSubtitle"></div>
            </div>

            <div class="track-lane">
              <div class="track-header">🔊 Audio</div>
              <div class="track-body" id="trackAudio"></div>
            </div>
          </div>
        </div>

        <!-- CỘT PHẢI: INSPECTOR TABS -->
        <div class="studio-inspector-col">
          <div class="inspector-tabs-header">
            <button class="tab-btn active" id="tabBtnCam" onclick="switchTab('camera')">📷 Quỹ Đạo</button>
            <button class="tab-btn" id="tabBtnCad" onclick="switchTab('cad')">🏗️ Kỹ Thuật CAD</button>
            <button class="tab-btn" id="tabBtnAudio" onclick="switchTab('audio')">🎙️ Thuyết Minh</button>
          </div>

          <!-- TAB 1: CAMERA -->
          <div id="tabContentCam">
            <h3 style="margin:4px 0;">Motion Presets Chuẩn Kỹ Thuật:</h3>
            <div class="preset-grid">
              <div class="preset-card-item" onclick="applyPreset('push_in')">
                <div class="preset-title">🎯 Push-In</div>
                <div class="preset-desc">Tiến gần công trình theo trục Z</div>
              </div>
              <div class="preset-card-item" onclick="applyPreset('pull_out')">
                <div class="preset-title">🔭 Pull-Out</div>
                <div class="preset-desc">Lùi xa mở rộng đại cảnh</div>
              </div>
              <div class="preset-card-item" onclick="applyPreset('orbit')">
                <div class="preset-title">🔄 Orbit 360</div>
                <div class="preset-desc">Xoay cung tròn quanh tâm</div>
              </div>
              <div class="preset-card-item" onclick="applyPreset('pan_lr')">
                <div class="preset-title">↔️ Pan Ngang</div>
                <div class="preset-desc">Trượt ngang trục X giữ góc</div>
              </div>
              <div class="preset-card-item" onclick="applyPreset('fly_through')">
                <div class="preset-title">🦅 Cần Cẩu (Crane)</div>
                <div class="preset-desc">Nâng cao độ bay bao quát</div>
              </div>
              <div class="preset-card-item" onclick="applyPreset('isometric')">
                <div class="preset-title">📐 Góc Xiên</div>
                <div class="preset-desc">Trực giao Isometric kỹ thuật</div>
              </div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
              <h3 style="margin:0;">Danh Sách Keyframes (<span id="kfCount">0</span>):</h3>
              <button class="secondary" style="padding:3px 8px; font-size:11px;" onclick="addKeyframe()">+ Thêm Điểm</button>
            </div>

            <div style="max-height:180px; overflow-y:auto; margin:6px 0;">
              <table class="kf-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>X</th>
                    <th>Y</th>
                    <th>Z</th>
                    <th>Focal</th>
                    <th>Xóa</th>
                  </tr>
                </thead>
                <tbody id="kfTableBody"></tbody>
              </table>
            </div>

            <div id="validationResultArea"></div>

            <div class="btn-row">
              <button style="flex:1;" onclick="validateCameraPath()">🔍 Xác Thực Quỹ Đạo</button>
              <button class="secondary" style="flex:1;" onclick="saveCameraPath()">💾 Lưu Camera Path</button>
            </div>
          </div>

          <!-- TAB 2: CAD / GIS -->
          <div id="tabContentCad" style="display:none;">
            <label style="font-size:11px; color:#94a3b8;">Tên phân cảnh:</label>
            <input id="shotNameInput" onchange="updateShotProp('name', this.value)" />

            <label style="font-size:11px; color:#94a3b8;">Thời lượng (giây):</label>
            <input type="number" id="shotDurInput" step="0.5" min="1" max="30" onchange="updateShotProp('duration_sec', parseFloat(this.value))" />

            <label style="font-size:11px; color:#94a3b8;">Chế độ Camera:</label>
            <select id="shotModeSelect" onchange="updateShotProp('camera_mode', this.value)">
              <option value="2D_IMAGE_CAMERA">2D_IMAGE_CAMERA (An toàn bảo toàn hình học CPU)</option>
              <option value="3D_COLMAP_NERFSTUDIO">3D_COLMAP_NERFSTUDIO (3DGS Splatfacto GPU)</option>
              <option value="HYBRID_SPLINE_NEURAL">HYBRID_SPLINE_NEURAL (Nội suy Spline)</option>
            </select>

            <label style="font-size:11px; color:#94a3b8;">Banner kỹ thuật / Lý trình:</label>
            <input id="shotTitleInput" placeholder="Ví dụ: Km 0+500 - Cầu Vượt Nút Giao Chính" onchange="updateShotProp('overlay_title', this.value)" />

            <div class="btn-row" style="margin-top:12px;">
              <button class="secondary" style="flex:1;" onclick="previewShot()">🎬 Render Xem Thử Shot</button>
            </div>
          </div>

          <!-- TAB 3: AUDIO & NARRATION -->
          <div id="tabContentAudio" style="display:none;">
            <label style="font-size:11px; color:#94a3b8;">Phụ đề kỹ thuật:</label>
            <textarea id="shotSubInput" rows="3" placeholder="Nhập nội dung phụ đề..." onchange="updateShotProp('subtitle_text', this.value)"></textarea>

            <label style="font-size:11px; color:#94a3b8;">Lời bình thuyết minh (AI Voiceover):</label>
            <textarea id="shotNarrInput" rows="4" placeholder="Nhập kịch bản thuyết minh..." onchange="updateShotProp('narration_text', this.value)"></textarea>

            <button class="secondary" style="width:100%; margin-top:8px;" onclick="alert('Đang mô phỏng phát giọng đọc thuyết minh...')">
              🔊 Thử Giọng Đọc Mô Phỏng
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 5. Render & Video QC -->
    <section class="card">
      <h2>5. Xuất Bản & Kiểm Tra Chất Lượng Video (QC)</h2>
      <div class="btn-row">
        <button class="secondary" id="timelineBtn" disabled onclick="renderTimeline()">🎞️ Xuất Toàn Bộ Video Dự Án (Timeline MP4 1080p)</button>
      </div>

      <div id="jobArea" style="display:none; margin-top: 14px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <p style="margin:0;"><strong id="jobType">Render</strong>: <span id="jobStatus" class="badge">Đang xử lý</span> · <span id="jobPercent">0%</span></p>
          <button class="danger" id="cancelJobBtn" style="padding:4px 10px; font-size:11px; display:none;" onclick="cancelJob()">🛑 Hủy Render (Cancel)</button>
        </div>
        <div class="progress"><div class="progress-bar" id="progressBar"></div></div>
        <div id="jobError" style="color:#f87171; display:none;"></div>
        <div id="qcReportArea" style="display:none;"></div>
        <div id="jobDownloadArea" style="margin: 12px 0;"></div>
      </div>
    </section>
  </main>

  <script>
    let projects = [];
    let currentProjectId = "";
    let assets = [];
    let shots = [];
    let selectedShot = null;
    let cameraPath = null;
    let currentJob = null;
    let pollTimer = null;

    // Studio Player state
    let currentTime = 0.0;
    let currentShotDuration = 5.0;
    let isPlaying = false;
    let animId = null;
    let lastTime = 0;
    let showGrid = true;
    let showSafeZone = true;
    let selectedKfIdx = null;

    async function init() {
      await loadCapabilities();
      await loadProjects();
      initAudioWaveform();
      renderRuler();
      requestAnimationFrame(drawCanvas);
    }

    async function loadCapabilities() {
      try {
        const res = await fetch("/api/v1/capabilities");
        if (!res.ok) return;
        const c = await res.json();
        const b = document.getElementById("capBadges");
        b.innerHTML = "";
        const cudaOk = c.cuda && c.cuda.available;
        b.innerHTML += `<span class="badge ${cudaOk ? 'badge-ok' : 'badge-warn'}">${cudaOk ? '🟢 CUDA: Sẵn sàng' : '🟡 Chế độ: Safe 2D Motion (CPU Fallback)'}</span>`;
        const colmapOk = c.colmap && c.colmap.available;
        b.innerHTML += `<span class="badge ${colmapOk ? 'badge-ok' : 'badge-warn'}">SfM / COLMAP: ${colmapOk ? 'Khả dụng' : 'Chưa cài'}</span>`;
        const nsTrain = c.nerfstudio && c.nerfstudio.train_available;
        b.innerHTML += `<span class="badge ${nsTrain ? 'badge-ok' : 'badge-warn'}">3DGS: ${nsTrain ? 'Sẵn sàng train' : 'Chờ GPU'}</span>`;
        const ffOk = c.ffmpeg && c.ffmpeg.available;
        b.innerHTML += `<span class="badge ${ffOk ? 'badge-ok' : 'badge-warn'}">FFmpeg: ${ffOk ? 'OK' : 'Thiếu'}</span>`;
        const ffpOk = c.ffprobe && c.ffprobe.available;
        b.innerHTML += `<span class="badge ${ffpOk ? 'badge-ok' : 'badge-info'}">FFprobe Deep QC: ${ffpOk ? 'Bật' : 'Dung lượng'}</span>`;
      } catch (e) {}
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
      } catch (e) {}
    }

    async function createProject() {
      const name = document.getElementById("projNameInput").value.trim();
      if (!name) return;
      const res = await fetch("/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      });
      const p = await res.json();
      document.getElementById("projNameInput").value = "";
      await loadProjects();
      currentProjectId = p.id;
      document.getElementById("projSelect").value = currentProjectId;
      onProjectChange();
    }

    async function onProjectChange() {
      currentProjectId = document.getElementById("projSelect").value;
      selectedShot = null;
      cameraPath = null;
      currentTime = 0;
      isPlaying = false;
      if (!currentProjectId) return;
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
    }

    async function uploadFiles(files) {
      if (!files || !currentProjectId) return;
      showMsg("Đang tải tệp lên...");
      for (const f of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", f);
        await fetch(`/api/v1/projects/${currentProjectId}/assets`, { method: "POST", body: fd });
      }
      showMsg("Đã tải ảnh lên thành công.");
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
        showMsg(`Đã gom nhóm: ${data.groups.length} nhóm cảnh hình học | ${data.unresolved.length} ảnh lẻ.`);
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
      }
    }

    async function loadShots() {
      if (!currentProjectId) return;
      const res = await fetch(`/api/v1/projects/${currentProjectId}`);
      const data = await res.json();
      shots = data.shots || [];
      document.getElementById("shotCountBadge").textContent = `${shots.length} Phân Cảnh`;
      document.getElementById("timelineBtn").disabled = (shots.length === 0);
      renderTimelineClips();
      if (!selectedShot && shots[0]) selectShot(shots[0]);
    }

    async function selectShot(s) {
      selectedShot = s;
      currentShotDuration = s.duration_sec || 5.0;
      currentTime = 0;
      isPlaying = false;
      document.getElementById("activeShotBadge").textContent = s.name;
      document.getElementById("hudCameraMode").textContent = `🎯 ${s.camera_mode || '2D_IMAGE_CAMERA'}`;
      document.getElementById("durText").textContent = `${currentShotDuration.toFixed(1)}s`;
      document.getElementById("fpsDisplay").textContent = `${s.fps || 30} FPS`;

      const hudTitle = document.getElementById("hudTitle");
      if (s.overlay_title) {
        hudTitle.style.display = "inline-block";
        hudTitle.textContent = `📌 ${s.overlay_title}`;
      } else {
        hudTitle.style.display = "none";
      }

      // Populate Inspector inputs
      document.getElementById("shotNameInput").value = s.name || "";
      document.getElementById("shotDurInput").value = currentShotDuration;
      document.getElementById("shotModeSelect").value = s.camera_mode || "2D_IMAGE_CAMERA";
      document.getElementById("shotTitleInput").value = s.overlay_title || "";
      document.getElementById("shotSubInput").value = s.subtitle_text || "";
      document.getElementById("shotNarrInput").value = s.narration_text || "";

      // Load Camera Path
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
      renderTimelineKeyframes();
      renderTimelineSubtitle();
      renderTimelineClips();
      renderRuler();
      updateScrubberUI();
    }

    function updateShotProp(prop, val) {
      if (!selectedShot) return;
      selectedShot[prop] = val;
      if (prop === 'duration_sec') {
        currentShotDuration = val;
        document.getElementById("durText").textContent = `${currentShotDuration.toFixed(1)}s`;
        renderRuler();
      }
      if (prop === 'overlay_title') {
        const hudTitle = document.getElementById("hudTitle");
        if (val) {
          hudTitle.style.display = "inline-block";
          hudTitle.textContent = `📌 ${val}`;
        } else {
          hudTitle.style.display = "none";
        }
        renderTimelineSubtitle();
      }
    }

    // Canvas Renderer
    function drawCanvas() {
      const canvas = document.getElementById("studioCanvas");
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const w = canvas.width;
      const h = canvas.height;

      ctx.fillStyle = "#050914";
      ctx.fillRect(0, 0, w, h);

      // Grid
      if (showGrid) {
        ctx.strokeStyle = "rgba(30, 58, 95, 0.35)";
        ctx.lineWidth = 1;
        for (let x = 0; x < w; x += 40) {
          ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
        }
        for (let y = 0; y < h; y += 40) {
          ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        }
        // Rule of thirds
        ctx.strokeStyle = "rgba(56, 189, 248, 0.2)";
        ctx.lineWidth = 1.5;
        [w / 3, (w * 2) / 3].forEach(gx => {
          ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, h); ctx.stroke();
        });
        [h / 3, (h * 2) / 3].forEach(gy => {
          ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke();
        });
      }

      // Safe Zone
      if (showSafeZone) {
        ctx.strokeStyle = "rgba(245, 158, 11, 0.35)";
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(w * 0.05, h * 0.05, w * 0.9, h * 0.9);
        ctx.setLineDash([]);
      }

      const cx = w / 2;
      const cy = h / 2;
      const scale = Math.min(w, h) * 0.3;

      if (cameraPath && cameraPath.keyframes && cameraPath.keyframes.length >= 2) {
        ctx.save();
        ctx.strokeStyle = "#0ea5e9";
        ctx.lineWidth = 3;
        ctx.beginPath();

        const pts = cameraPath.keyframes.map(k => ({
          x: cx + k.position[0] * scale,
          y: cy + (k.position[2] + 1.5) * scale * 0.8,
          k
        }));

        pts.forEach((pt, idx) => {
          if (idx === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();

        // Keyframe markers
        pts.forEach((pt, idx) => {
          const isSel = selectedKfIdx === idx;
          ctx.save();
          ctx.translate(pt.x, pt.y);
          // Frustum
          ctx.strokeStyle = isSel ? "#f59e0b" : "rgba(56, 189, 248, 0.4)";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(0, 0); ctx.lineTo(-14, -22); ctx.lineTo(14, -22); ctx.closePath();
          ctx.stroke();
          // Diamond
          ctx.rotate(Math.PI / 4);
          ctx.fillStyle = isSel ? "#f59e0b" : "#0284c7";
          ctx.fillRect(-6, -6, 12, 12);
          ctx.strokeStyle = "#fff";
          ctx.strokeRect(-6, -6, 12, 12);
          ctx.restore();

          ctx.font = "bold 10px monospace";
          ctx.fillStyle = isSel ? "#fef08a" : "#cbd5e1";
          ctx.fillText(`KF${idx + 1} (${pt.k.timestamp_sec.toFixed(1)}s)`, pt.x + 10, pt.y - 10);
        });

        // Animated camera position
        const tNorm = Math.min(1.0, Math.max(0.0, currentTime / (currentShotDuration || 5.0)));
        const kfA = cameraPath.keyframes[0];
        const kfB = cameraPath.keyframes[cameraPath.keyframes.length - 1];
        const curX = cx + (kfA.position[0] + (kfB.position[0] - kfA.position[0]) * tNorm) * scale;
        const curY = cy + (kfA.position[2] + (kfB.position[2] - kfA.position[2]) * tNorm + 1.5) * scale * 0.8;

        ctx.save();
        ctx.translate(curX, curY);
        ctx.fillStyle = "#ef4444";
        ctx.beginPath(); ctx.arc(0, 0, 8, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.stroke();

        ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(-24, -40); ctx.lineTo(24, -40); ctx.closePath(); ctx.fill();
        ctx.restore();

        ctx.restore();
      } else {
        ctx.font = "14px sans-serif";
        ctx.fillStyle = "#64748b";
        ctx.textAlign = "center";
        ctx.fillText("📷 Chưa có Camera Path. Chọn Preset ở cột phải để tạo.", cx, cy);
        ctx.textAlign = "start";
      }

      // Technical Title
      if (selectedShot && selectedShot.overlay_title) {
        ctx.save();
        ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
        ctx.strokeStyle = "#0284c7";
        ctx.lineWidth = 1;
        ctx.fillRect(w * 0.1, h * 0.78, w * 0.8, 38);
        ctx.strokeRect(w * 0.1, h * 0.78, w * 0.8, 38);
        ctx.font = "bold 13px sans-serif";
        ctx.fillStyle = "#38bdf8";
        ctx.fillText(selectedShot.overlay_title, w * 0.12, h * 0.82 + 5);
        ctx.restore();
      }

      if (isPlaying) {
        const now = performance.now();
        const dt = (now - lastTime) / 1000;
        lastTime = now;
        currentTime += dt;
        if (currentTime >= currentShotDuration) {
          currentTime = currentShotDuration;
          togglePlay();
        }
        updateScrubberUI();
      }

      requestAnimationFrame(drawCanvas);
    }

    function togglePlay() {
      isPlaying = !isPlaying;
      lastTime = performance.now();
      const btn = document.getElementById("playBtn");
      btn.textContent = isPlaying ? "⏸ Tạm Dừng" : "▶ Phát";
      btn.classList.toggle("play", !isPlaying);
    }

    function seekTime(t) {
      currentTime = Math.max(0, Math.min(currentShotDuration, t));
      updateScrubberUI();
    }

    function handleScrub(e) {
      const rect = e.currentTarget.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      currentTime = pct * currentShotDuration;
      updateScrubberUI();
    }

    function updateScrubberUI() {
      const pct = Math.min(100, Math.max(0, (currentTime / (currentShotDuration || 5.0)) * 100));
      document.getElementById("scrubberProgress").style.width = `${pct}%`;
      const curFmt = formatTimecode(currentTime);
      const totalFmt = formatTimecode(currentShotDuration);
      document.getElementById("timecodeDisplay").textContent = `${curFmt} / ${totalFmt}`;
    }

    function formatTimecode(sec, fps = 30) {
      const totalFrames = Math.floor(sec * fps);
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      const f = totalFrames % fps;
      const pad = n => String(n).padStart(2, "0");
      return `${pad(m)}:${pad(s)}:${pad(f)}`;
    }

    function toggleGrid() {
      showGrid = !showGrid;
      document.getElementById("btnToggleGrid").classList.toggle("active", showGrid);
    }

    function toggleSafeZone() {
      showSafeZone = !showSafeZone;
      document.getElementById("btnToggleSafe").classList.toggle("active", showSafeZone);
    }

    function switchTab(t) {
      document.getElementById("tabContentCam").style.display = t === 'camera' ? 'block' : 'none';
      document.getElementById("tabContentCad").style.display = t === 'cad' ? 'block' : 'none';
      document.getElementById("tabContentAudio").style.display = t === 'audio' ? 'block' : 'none';
      document.getElementById("tabBtnCam").classList.toggle("active", t === 'camera');
      document.getElementById("tabBtnCad").classList.toggle("active", t === 'cad');
      document.getElementById("tabBtnAudio").classList.toggle("active", t === 'audio');
    }

    // Timeline Rendering
    function renderRuler() {
      const r = document.getElementById("timelineRuler");
      r.innerHTML = "";
      const dur = Math.ceil(currentShotDuration || 5);
      for (let s = 0; s <= dur; s++) {
        const pct = (s / (currentShotDuration || 5)) * 100;
        const tick = document.createElement("div");
        tick.className = "ruler-tick";
        tick.style.left = `${pct}%`;
        tick.textContent = `${s}s`;
        r.appendChild(tick);
      }
    }

    function renderTimelineClips() {
      const c = document.getElementById("trackVideoClips");
      c.innerHTML = "";
      shots.forEach((s, idx) => {
        const div = document.createElement("div");
        div.className = "shot-clip-item" + (selectedShot && selectedShot.id === s.id ? " active" : "");
        div.style.flex = s.duration_sec || 5;
        div.onclick = () => selectShot(s);
        div.innerHTML = `<span>#${idx + 1} ${s.name}</span><span style="font-size:9.5px;opacity:0.8;">${s.duration_sec}s</span>`;
        c.appendChild(div);
      });
    }

    function renderTimelineKeyframes() {
      const t = document.getElementById("trackKeyframes");
      t.innerHTML = "";
      if (!cameraPath || !cameraPath.keyframes) return;
      cameraPath.keyframes.forEach((kf, idx) => {
        const pct = Math.min(100, Math.max(0, (kf.timestamp_sec / (currentShotDuration || 5)) * 100));
        const d = document.createElement("div");
        d.className = "kf-diamond-marker" + (selectedKfIdx === idx ? " selected" : "");
        d.style.left = `${pct}%`;
        d.onclick = (e) => {
          e.stopPropagation();
          selectedKfIdx = idx;
          currentTime = kf.timestamp_sec;
          updateScrubberUI();
          renderKeyframesTable();
        };
        t.appendChild(d);
      });
    }

    function renderTimelineSubtitle() {
      const t = document.getElementById("trackSubtitle");
      const title = selectedShot ? (selectedShot.overlay_title || selectedShot.subtitle_text || "Chưa có phụ đề") : "";
      t.innerHTML = `<div style="height:22px;background:#1e3a5f;border-radius:4px;padding:0 8px;display:flex;align-items:center;font-size:10.5px;color:#93c5fd;width:100%;">${title}</div>`;
    }

    function initAudioWaveform() {
      const a = document.getElementById("trackAudio");
      let bars = '<div style="display:flex;align-items:center;height:100%;padding:0 8px;">';
      for (let i = 0; i < 48; i++) {
        const h = Math.round(18 + Math.sin(i * 0.5) * 14);
        bars += `<div class="wf-bar" style="height:${h}px;"></div>`;
      }
      bars += '</div>';
      a.innerHTML = bars;
    }

    function renderKeyframesTable() {
      const tbody = document.getElementById("kfTableBody");
      tbody.innerHTML = "";
      if (!cameraPath || !cameraPath.keyframes || !cameraPath.keyframes.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="color:#94a3b8;text-align:center;">Chưa có Keyframe nào.</td></tr>';
        document.getElementById("kfCount").textContent = "0";
        return;
      }
      document.getElementById("kfCount").textContent = cameraPath.keyframes.length;
      cameraPath.keyframes.forEach((kf, idx) => {
        const tr = document.createElement("tr");
        if (selectedKfIdx === idx) tr.style.background = "#172554";
        tr.onclick = () => {
          selectedKfIdx = idx;
          currentTime = kf.timestamp_sec;
          updateScrubberUI();
          renderTimelineKeyframes();
        };
        tr.innerHTML = `
          <td><strong>${idx + 1}</strong></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.timestamp_sec}" onchange="updateKf(${idx}, 't', this.value)" /></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.position[0]}" onchange="updateKf(${idx}, 'x', this.value)" /></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.position[1]}" onchange="updateKf(${idx}, 'y', this.value)" /></td>
          <td><input class="kf-input" type="number" step="0.1" value="${kf.position[2]}" onchange="updateKf(${idx}, 'z', this.value)" /></td>
          <td><input class="kf-input" type="number" step="1" value="${kf.focal_length_mm}" onchange="updateKf(${idx}, 'focal', this.value)" /></td>
          <td><button class="danger" style="padding:2px 6px;font-size:10px;" ${cameraPath.keyframes.length <= 2 ? 'disabled' : ''} onclick="removeKf(event, ${idx})">×</button></td>
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
      renderTimelineKeyframes();
    }

    function addKeyframe() {
      if (!cameraPath) { applyPreset('push_in'); return; }
      const last = cameraPath.keyframes[cameraPath.keyframes.length - 1];
      cameraPath.keyframes.push({
        id: `kf_${cameraPath.keyframes.length + 1}`,
        position: last ? [last.position[0], last.position[1], last.position[2] + 0.3] : [0, 0, -1],
        rotation_quaternion: [0, 0, 0, 1],
        quaternion_order: "xyzw",
        timestamp_sec: last ? Math.min(currentShotDuration, last.timestamp_sec + 1.0) : 1.0,
        focal_length_mm: 35.0,
        sensor_width_mm: 36.0,
        confidence: 1.0,
        locked: false
      });
      renderKeyframesTable();
      renderTimelineKeyframes();
    }

    function removeKf(e, idx) {
      e.stopPropagation();
      if (!cameraPath || cameraPath.keyframes.length <= 2) return;
      cameraPath.keyframes.splice(idx, 1);
      selectedKfIdx = null;
      renderKeyframesTable();
      renderTimelineKeyframes();
    }

    function applyPreset(p) {
      if (!selectedShot) return;
      const dur = currentShotDuration;
      let kfs = [];
      if (p === 'push_in') {
        kfs = [
          { id: "kf_1", position: [0, 0, -2.5], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0, 0, -0.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else if (p === 'pull_out') {
        kfs = [
          { id: "kf_1", position: [0, 0, -0.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0, 0, -2.5], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else if (p === 'orbit') {
        kfs = [
          { id: "kf_1", position: [-1.6, 0.5, -2.0], rotation_quaternion: [0, 0.22, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0.0, 0.7, -2.3], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur * 0.5, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_3", position: [1.6, 0.5, -2.0], rotation_quaternion: [0, -0.22, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 35.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else if (p === 'pan_lr') {
        kfs = [
          { id: "kf_1", position: [-1.3, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [1.3, 0, -1.8], rotation_quaternion: [0, 0, 0, 1], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else if (p === 'fly_through') {
        kfs = [
          { id: "kf_1", position: [0, -0.5, -2.6], rotation_quaternion: [-0.06, 0, 0, 0.998], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 28.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0, 0.9, -0.5], rotation_quaternion: [0.12, 0, 0, 0.992], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 32.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      } else {
        kfs = [
          { id: "kf_1", position: [-1.2, 1.2, -1.8], rotation_quaternion: [0.15, 0.15, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: 0.0, focal_length_mm: 50.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false },
          { id: "kf_2", position: [0.8, 1.2, -1.8], rotation_quaternion: [0.15, -0.15, 0, 0.97], quaternion_order: "xyzw", timestamp_sec: dur, focal_length_mm: 50.0, sensor_width_mm: 36.0, confidence: 1.0, locked: false }
        ];
      }
      cameraPath = {
        schema_version: 1, duration_sec: dur, fps: selectedShot.fps || 30, width: 1920, height: 1080,
        easing: "cinematic", path_type: "catmull_rom", tension: 0.5, keyframes: kfs
      };
      selectedKfIdx = null;
      renderKeyframesTable();
      renderTimelineKeyframes();
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
              <span>${val.ok ? '✅ QUỸ ĐẠO HỢP LỆ' : '❌ TỪ CHỐI QUỸ ĐẠO'}</span>
              <span>Điểm: ${(val.score * 100).toFixed(1)}%</span>
            </div>
            ${val.rejection_reasons.length > 0 ? '<ul style="margin:4px 0 0 16px;padding:0;">' + val.rejection_reasons.map(r => `<li>${r}</li>`).join('') + '</ul>' : ''}
          </div>
        `;
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
      }
    }

    async function cancelJob() {
      if (!currentJob) return;
      const res = await fetch(`/api/v1/render-jobs/${currentJob.id}/cancel`, { method: "POST" });
      if (res.ok) {
        currentJob = await res.json();
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
    return HTMLResponse(content=HTML_CONTENT, status_code=200)
