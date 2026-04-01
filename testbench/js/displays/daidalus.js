/**
 * DAIDALUS: top-down map + heading band (synthetic intruder when alert > 0 — no intruder topic in spec)
 */
const DaidalusDisplay = {
  mapCanvas: null,
  hdgCanvas: null,
  mount(parent) {
    const wrap = document.createElement("div");
    wrap.className = "display-row";
    wrap.innerHTML = `
      <div>
        <h2 class="section-title">DAIDALUS — mapa horizontal</h2>
        <canvas class="map-canvas" width="420" height="280" id="dai-map"></canvas>
      </div>
      <div>
        <h2 class="section-title">Heading 360° (sintético si alerta)</h2>
        <canvas class="map-canvas" width="280" height="280" id="dai-hdg"></canvas>
        <div id="dai-badge" style="margin-top:8px;font-size:18px;font-weight:700;color:#4a9eff;">ALERT: —</div>
      </div>
    `;
    parent.appendChild(wrap);
    this.mapCanvas = document.getElementById("dai-map");
    this.hdgCanvas = document.getElementById("dai-hdg");
  },

  update(st) {
    const level = st.daidalusLevel != null ? st.daidalusLevel : 0;
    const badge = document.getElementById("dai-badge");
    const names = ["NONE", "FAR", "MID", "NEAR"];
    if (badge) {
      badge.textContent = "alert_level: " + (names[level] || String(level));
      badge.style.color = level >= 3 ? "#ff5252" : level === 2 ? "#ffab40" : level === 1 ? "#ffee58" : "#4a9eff";
    }
    this._drawMap(level);
    this._drawHdg(level);
  },

  _drawMap(level) {
    const c = this.mapCanvas;
    if (!c) return;
    const ctx = c.getContext("2d");
    const W = c.width;
    const H = c.height;
    const cx = W / 2;
    const cy = H / 2;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, W, H);
    [100, 200, 500].forEach((r, i) => {
      ctx.beginPath();
      ctx.arc(cx, cy, r * 0.35, 0, Math.PI * 2);
      ctx.strokeStyle = ["#1e4a3a", "#2a5a44", "#3a6a55"][i];
      ctx.lineWidth = 1;
      ctx.stroke();
    });
    ctx.fillStyle = "#00e676";
    ctx.beginPath();
    ctx.arc(cx, cy, 8, 0, Math.PI * 2);
    ctx.fill();
    const pulse = 40 + level * 25;
    const col = level >= 3 ? "#ff5252" : level === 2 ? "#ffab40" : "#ffee58";
    if (level > 0) {
      ctx.beginPath();
      ctx.arc(cx + 120, cy - 30, 10, 0, Math.PI * 2);
      ctx.fillStyle = "#ff5252";
      ctx.fill();
      ctx.strokeStyle = col;
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      ctx.arc(cx + 120, cy - 30, pulse, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(cx + 120, cy - 30);
      ctx.lineTo(cx + 120 - 40, cy - 10);
      ctx.strokeStyle = "#ff8a80";
      ctx.stroke();
    }
    ctx.fillStyle = "#8aa4bc";
    ctx.font = "10px monospace";
    ctx.fillText("UAS centro · intruso sintético si alerta>0", 8, H - 8);
  },

  _drawHdg(level) {
    const c = this.hdgCanvas;
    if (!c) return;
    const ctx = c.getContext("2d");
    const s = c.width;
    const cx = s / 2;
    const cy = s / 2;
    const r = s * 0.42;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, s, s);
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = "#2a4a66";
    ctx.stroke();
    const conflict = (Math.PI / 3) * 1.2;
    const rec = -Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r - 8, rec - conflict / 2, rec + conflict / 2);
    ctx.closePath();
    ctx.fillStyle = "rgba(255,82,82,0.35)";
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r - 8, rec + Math.PI - 0.4, rec + Math.PI + 0.4);
    ctx.closePath();
    ctx.fillStyle = "rgba(0,230,118,0.35)";
    ctx.fill();
    ctx.fillStyle = "#e0e8f0";
    ctx.font = "11px monospace";
    ctx.fillText("N", cx - 4, cy - r - 4);
  },
};

window.DaidalusDisplay = DaidalusDisplay;
