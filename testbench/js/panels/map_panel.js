/**
 * Mapa 700×400: NFZ, ruta, trail por calidad, UAS con color FSM.
 */
class MapPanelCanvas extends Map2D {
  constructor(canvas) {
    super(canvas);
    this.nfzViolation = false;
    this.fsmMode = "";
    this._nfzPulse = 0;
  }

  setFsmMode(m) {
    this.fsmMode = m || "";
  }

  _pointInNfz(px, py) {
    return this.nfz.some((z) => px >= z.x && px <= z.x + z.w && py >= z.y && py <= z.y + z.h);
  }

  render() {
    const ctx = this.ctx;
    const W = this.canvas.width;
    const H = this.canvas.height;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#1e3a52";
    for (let x = 0; x < W; x += 20) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let y = 0; y < H; y += 20) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    this.nfz.forEach((z) => {
      ctx.fillStyle = "rgba(255,82,82,0.12)";
      ctx.fillRect(z.x, z.y, z.w, z.h);
      ctx.save();
      ctx.beginPath();
      ctx.rect(z.x, z.y, z.w, z.h);
      ctx.clip();
      ctx.strokeStyle = "rgba(255,82,82,0.35)";
      ctx.lineWidth = 1;
      for (let i = 0; i < z.w + z.h; i += 8) {
        ctx.beginPath();
        ctx.moveTo(z.x + i, z.y);
        ctx.lineTo(z.x + i - z.h, z.y + z.h);
        ctx.stroke();
      }
      ctx.restore();
      ctx.strokeStyle = "#ff5252";
      ctx.lineWidth = this.nfzViolation && Date.now() < this._nfzPulse ? 4 : 2;
      ctx.strokeRect(z.x, z.y, z.w, z.h);
      ctx.fillStyle = "#ff8a80";
      ctx.font = "10px monospace";
      ctx.fillText("NFZ", z.x + 4, z.y + 14);
    });

    const drawRoute = (pts, color, dash) => {
      if (!pts || pts.length < 2) return;
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash(dash || []);
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.stroke();
      ctx.setLineDash([]);
    };

    if (Date.now() < this.altUntil && this.routeAlt.length >= 2) {
      drawRoute(this.routeAlt, "#ffeb3b", [6, 4]);
    }
    drawRoute(this.routeActive, "#4a9eff", [8, 4]);

    this.waypoints.forEach((p, i) => {
      ctx.fillStyle = "#4a9eff";
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#e0e8f0";
      ctx.font = "10px monospace";
      ctx.fillText(String(i + 1), p.x + 6, p.y - 6);
    });

    const now = Date.now();
    const q = this._vq != null ? this._vq : 1;
    for (let i = 0; i < this.trail.length - 1; i++) {
      const a = this.trail[i];
      const b = this.trail[i + 1];
      const age = 1 - (now - b.t) / this.maxTrailMs;
      const o = 0.08 + 0.6 * age * q;
      ctx.strokeStyle = `rgba(0,230,118,${o.toFixed(3)})`;
      ctx.lineWidth = 0.8 + q * 2.5;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    if (this._vn != null && this._ve != null) {
      const px = this._ve;
      const py = -this._vn;
      const col = (window.FSM_COLORS && window.FSM_COLORS[this.fsmMode]) || "#00bcd4";
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.moveTo(px + 10, py);
      ctx.lineTo(px - 6, py - 5);
      ctx.lineTo(px - 6, py + 5);
      ctx.closePath();
      ctx.fill();
    }

    ctx.fillStyle = "#8aa4bc";
    ctx.font = "11px monospace";
    ctx.fillText("MapPanel · NED→screen", 8, H - 8);
  }

  updateViolationFromVehicle() {
    if (this._vn == null || this._ve == null) return;
    const px = this._ve;
    const py = -this._vn;
    const inside = this._pointInNfz(px, py);
    if (inside && !this.nfzViolation) this._nfzPulse = Date.now() + 800;
    this.nfzViolation = inside;
  }
}

class MapPanel extends BasePanel {
  mount() {
    this.container.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "map-panel-root";
    const overlay = document.createElement("div");
    overlay.className = "map-quality-overlay";
    overlay.id = "map-q-overlay";
    overlay.innerHTML =
      '<div class="map-q-big" id="map-q-val">—</div><div class="map-q-light" id="map-q-light"></div><div class="map-q-caption">quality_flag</div>';
    const c = document.createElement("canvas");
    c.width = 700;
    c.height = 400;
    c.className = "map-canvas map-panel-canvas";
    wrap.appendChild(overlay);
    wrap.appendChild(c);
    const badge = document.createElement("div");
    badge.className = "nfz-violation-badge";
    badge.id = "nfz-violation-badge";
    badge.textContent = "VIOLACIÓN";
    badge.style.display = "none";
    wrap.appendChild(badge);
    this.container.appendChild(wrap);
    this._mapRoot = wrap;
    this._map = new MapPanelCanvas(c);
    this._map.waypoints = [
      { x: 60, y: 340 },
      { x: 200, y: 280 },
      { x: 380, y: 200 },
      { x: 580, y: 120 },
    ];
    this._map.setActiveRoute(this._map.waypoints);
  }

  syncFromState(st) {
    if (this._frozen) return;
    const mode = (st.fsmState && st.fsmState.current_mode) || st.legacyMode || "";
    this._map.setFsmMode(mode);
    const arr = st.vehicleState;
    const q = st.quality != null ? st.quality : 1;
    if (arr && arr.length >= 3) {
      const n = Number(arr[0]);
      const e = Number(arr[1]);
      this._map.setVehicle(n, e, q);
    }
    this._map.updateViolationFromVehicle();
    const badge = this._mapRoot && this._mapRoot.querySelector("#nfz-violation-badge");
    if (badge) {
      badge.style.display = this._map.nfzViolation ? "block" : "none";
      if (this._map.nfzViolation) {
        badge.style.animation = "nfz-pulse 0.6s ease-in-out infinite";
      }
    }
    const qEl = this._mapRoot && this._mapRoot.querySelector("#map-q-val");
    const light = this._mapRoot && this._mapRoot.querySelector("#map-q-light");
    if (qEl) qEl.textContent = st.quality != null ? st.quality.toFixed(2) : "—";
    if (light) {
      light.className = "map-q-light";
      if (st.quality == null) light.classList.add("q-na");
      else if (st.quality > 0.7) light.classList.add("q-ok");
      else if (st.quality >= 0.5) light.classList.add("q-warn");
      else light.classList.add("q-bad");
    }
    this._map.render();
  }
}

window.MapPanel = MapPanel;
window.MapPanelCanvas = MapPanelCanvas;
