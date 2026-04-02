/**
 * DAIDALUS: PPI + bandas 360° (M5/M6). Suscripción a /daidalus/alert_level vía BasePanel.
 */
class RadarPanel extends BasePanel {
  mount() {
    this.container.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "radar-panel-grid";
    wrap.innerHTML = `
      <div class="radar-ppi-wrap">
        <div class="radar-dist radar-dist-label">Dist. horizontal: — m</div>
        <canvas width="360" height="360" class="map-canvas radar-ppi-canvas"></canvas>
      </div>
      <div class="radar-hdg-wrap">
        <canvas width="320" height="320" class="map-canvas radar-hdg-canvas"></canvas>
        <div class="radar-alert-badge radar-alert-badge-el">NONE</div>
      </div>
    `;
    this.container.appendChild(wrap);
    this._wrap = wrap;
    this._ppi = wrap.querySelector(".radar-ppi-canvas");
    this._hdg = wrap.querySelector(".radar-hdg-canvas");
    this._distLabel = wrap.querySelector(".radar-dist-label");
    this._badgeEl = wrap.querySelector(".radar-alert-badge-el");
    this._level = 0;
    this._distM = 420;
    this.subscribeRos("/daidalus/alert_level", "std_msgs/Int32", (msg) => {
      this._level = msg.data != null ? parseInt(msg.data, 10) : 0;
      this._paint();
    });
  }

  handleTopic(topic, msg) {
    if (topic === "/daidalus/alert_level" && msg && msg.data != null) {
      this._level = parseInt(msg.data, 10);
      this._paint();
    }
  }

  syncFromState(st) {
    if (this._frozen) return;
    const level = st.daidalusLevel != null ? st.daidalusLevel : this._level;
    this._level = level;
    this._paint();
  }

  _paint() {
    const level = this._level;
    const names = ["NONE", "FAR", "MID", "NEAR", "COLLISION"];
    if (this._badgeEl) {
      const label = names[level] || String(level);
      this._badgeEl.textContent = label;
      this._badgeEl.className = "radar-alert-badge radar-alert-badge-el lvl-" + level;
    }
    if (this._distLabel) {
      this._distLabel.textContent = "Dist. horizontal intruso: ~" + this._distM + " m (sintético)";
    }
    this._drawPpi(level);
    this._drawHdg(level);
  }

  _drawPpi(level) {
    const c = this._ppi;
    if (!c) return;
    const ctx = c.getContext("2d");
    const W = c.width;
    const H = c.height;
    const cx = W / 2;
    const cy = H / 2;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, W, H);
    const rings = [100, 300, 500];
    rings.forEach((r, i) => {
      const rad = (r / 500) * (W * 0.42);
      ctx.beginPath();
      ctx.arc(cx, cy, rad, 0, Math.PI * 2);
      ctx.strokeStyle = ["#1e4a3a", "#2a5a44", "#3a6a55"][i];
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = "#6a8aaa";
      ctx.font = "9px monospace";
      ctx.fillText(r + "m", cx + rad - 18, cy - 2);
    });
    const zoneR = 40 + level * 28;
    const colors = ["rgba(0,230,118,0.15)", "rgba(255,238,88,0.2)", "rgba(255,171,64,0.25)", "rgba(255,82,82,0.35)", "rgba(255,0,0,0.45)"];
    ctx.beginPath();
    ctx.arc(cx, cy, zoneR, 0, Math.PI * 2);
    ctx.fillStyle = colors[Math.min(level, 4)];
    ctx.fill();
    ctx.fillStyle = "#00e676";
    ctx.beginPath();
    ctx.arc(cx, cy, 8, 0, Math.PI * 2);
    ctx.fill();
    if (level > 0) {
      const ix = cx + 110;
      const iy = cy - 40;
      ctx.fillStyle = "#ff5252";
      ctx.beginPath();
      ctx.arc(ix, iy, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#ffab40";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(ix, iy);
      ctx.lineTo(ix - 35, iy + 12);
      ctx.stroke();
    }
    ctx.fillStyle = "#8aa4bc";
    ctx.font = "10px monospace";
    ctx.fillText("PPI · UAS centro", 8, H - 6);
  }

  _drawHdg(level) {
    const c = this._hdg;
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
    const sectors = 12;
    for (let i = 0; i < sectors; i++) {
      const a0 = (i / sectors) * Math.PI * 2 - Math.PI / 2;
      const a1 = ((i + 1) / sectors) * Math.PI * 2 - Math.PI / 2;
      const conflict = level > 0 && (i === 2 || i === 3);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r - 10, a0, a1);
      ctx.closePath();
      ctx.fillStyle = conflict ? "rgba(255,82,82,0.4)" : "rgba(40,60,80,0.2)";
      ctx.fill();
    }
    const recA = -Math.PI / 2 + 0.3;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r - 10, recA - 0.25, recA + 0.25);
    ctx.closePath();
    ctx.fillStyle = "rgba(0,230,118,0.45)";
    ctx.fill();
    ctx.strokeStyle = "#e0e8f0";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(recA) * (r - 14), cy + Math.sin(recA) * (r - 14));
    ctx.stroke();
    ctx.fillStyle = "#b8d4f0";
    ctx.font = "10px monospace";
    ctx.fillText("N", cx - 3, cy - r - 4);
    if (level > 0) {
      ctx.fillStyle = "#69f0ae";
      ctx.font = "11px monospace";
      ctx.fillText("↗ hdg recomendado", cx - 48, cy + r + 14);
    }
  }
}

window.RadarPanel = RadarPanel;
