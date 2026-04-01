/**
 * 2D top-down map: UAS position, trail, NFZ, optional waypoints/route
 */
class Map2D {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.nfz = [
      { x: 80, y: 90, w: 100, h: 70 },
      { x: 220, y: 140, w: 90, h: 60 },
    ];
    this.waypoints = [];
    this.routeActive = [];
    this.routeAlt = [];
    this.altUntil = 0;
    /** @type {Array<{x:number,y:number,t:number}>} */
    this.trail = [];
    this.maxTrailMs = 120000;
  }

  setVehicle(n, e, quality) {
    const now = Date.now();
    this._vn = n;
    this._ve = e;
    this._vq = quality;
    this.trail.push({ x: e, y: -n, t: now });
    this.trail = this.trail.filter((p) => now - p.t < this.maxTrailMs);
  }

  setWaypoints(wps) {
    this.waypoints = wps || [];
  }

  /** highlight alternate route for ms */
  setReplanRoute(route, ms = 3000) {
    this.routeAlt = route || [];
    this.altUntil = Date.now() + ms;
  }

  setActiveRoute(route) {
    this.routeActive = route || [];
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

    ctx.fillStyle = "rgba(255,82,82,0.25)";
    this.nfz.forEach((z) => {
      ctx.fillRect(z.x, z.y, z.w, z.h);
      ctx.strokeStyle = "#ff5252";
      ctx.strokeRect(z.x, z.y, z.w, z.h);
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
      drawRoute(this.routeAlt, "#4a9eff", [6, 4]);
    }
    drawRoute(this.routeActive, "#69f0ae", []);

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
    for (let i = 0; i < this.trail.length - 1; i++) {
      const a = this.trail[i];
      const b = this.trail[i + 1];
      const age = 1 - (now - b.t) / this.maxTrailMs;
      const o = 0.15 + 0.55 * age * (this._vq != null ? this._vq : 1);
      ctx.strokeStyle = `rgba(0,230,118,${o.toFixed(3)})`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    if (this._vn != null && this._ve != null) {
      const px = this._ve;
      const py = -this._vn;
      ctx.fillStyle = "#00bcd4";
      ctx.beginPath();
      ctx.arc(px, py, 6, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.fillStyle = "#8aa4bc";
    ctx.font = "11px monospace";
    ctx.fillText("Map2D (NED→x=east, y=-north)", 8, H - 8);
  }
}

window.Map2D = Map2D;
