/**
 * Vista plana de la polilínea /gpp/global_path (nav_msgs/Path).
 */
class GppRrtPanel extends BasePanel {
  mount() {
    this.container.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "gpp-rrt-panel";
    const title = document.createElement("div");
    title.className = "gpp-rrt-title";
    title.textContent = "GPP global_path (NED x,y → pantalla)";
    const cv = document.createElement("canvas");
    cv.className = "gpp-rrt-canvas map-canvas";
    cv.width = 420;
    cv.height = 320;
    wrap.appendChild(title);
    wrap.appendChild(cv);
    this.container.appendChild(wrap);
    this._canvas = cv;
    this._poses = [];
    this.subscribeRos("/gpp/global_path", "nav_msgs/Path", (msg) => {
      this._poses = (msg.poses || []).map((ps) => ({
        x: ps.pose.position.x,
        y: ps.pose.position.y,
      }));
      this._draw();
    });
  }

  handleTopic(topic, msg) {
    if (topic === "/gpp/global_path" && msg && msg.poses) {
      this._poses = msg.poses.map((ps) => ({
        x: ps.pose.position.x,
        y: ps.pose.position.y,
      }));
      this._draw();
    }
  }

  _draw() {
    const c = this._canvas;
    if (!c) return;
    const ctx = c.getContext("2d");
    const W = c.width;
    const H = c.height;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#1e3a52";
    ctx.lineWidth = 1;
    for (let g = 0; g < W; g += 20) {
      ctx.beginPath();
      ctx.moveTo(g, 0);
      ctx.lineTo(g, H);
      ctx.stroke();
    }
    for (let g = 0; g < H; g += 20) {
      ctx.beginPath();
      ctx.moveTo(0, g);
      ctx.lineTo(W, g);
      ctx.stroke();
    }
    if (this._poses.length < 2) {
      ctx.fillStyle = "#6a8aaa";
      ctx.font = "11px monospace";
      ctx.fillText("Sin ruta (esperando /gpp/global_path)", 12, H / 2);
      return;
    }
    let minX = this._poses[0].x;
    let maxX = minX;
    let minY = this._poses[0].y;
    let maxY = minY;
    this._poses.forEach((p) => {
      minX = Math.min(minX, p.x);
      maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y);
      maxY = Math.max(maxY, p.y);
    });
    const pad = 40;
    const dx = Math.max(1e-6, maxX - minX);
    const dy = Math.max(1e-6, maxY - minY);
    const sx = (W - 2 * pad) / dx;
    const sy = (H - 2 * pad) / dy;
    const sc = Math.min(sx, sy);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const toCanvas = (px, py) => ({
      x: W / 2 + (px - cx) * sc,
      y: H / 2 - (py - cy) * sc,
    });
    ctx.strokeStyle = "#4a9eff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    this._poses.forEach((p, i) => {
      const q = toCanvas(p.x, p.y);
      if (i === 0) ctx.moveTo(q.x, q.y);
      else ctx.lineTo(q.x, q.y);
    });
    ctx.stroke();
    const start = toCanvas(this._poses[0].x, this._poses[0].y);
    ctx.fillStyle = "#00e676";
    ctx.beginPath();
    ctx.arc(start.x, start.y, 6, 0, Math.PI * 2);
    ctx.fill();
    const end = toCanvas(this._poses[this._poses.length - 1].x, this._poses[this._poses.length - 1].y);
    ctx.fillStyle = "#ffab40";
    ctx.beginPath();
    ctx.arc(end.x, end.y, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#8aa4bc";
    ctx.font = "10px monospace";
    ctx.fillText(`poses: ${this._poses.length}`, 8, H - 6);
  }
}

window.GppRrtPanel = GppRrtPanel;
