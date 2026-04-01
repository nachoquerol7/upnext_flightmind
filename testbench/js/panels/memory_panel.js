/**
 * RAM por proceso (localhost:9091) — TC-E2E-007
 */
class MemoryPanel extends BasePanel {
  constructor(container, ros) {
    super(container, ros);
    this._interval = null;
    this._series = {};
    this._t0 = 0;
    this._thresholdMb = 10;
  }

  mount() {
    this.container.innerHTML = "";
    const head = document.createElement("div");
    head.className = "memory-head";
    head.innerHTML =
      '<div>RAM por nodo (MB) · umbral crecimiento <span id="mem-th">10</span> MB</div><div id="mem-fail" class="mem-fail-badge"></div>';
    this.container.appendChild(head);
    const c = document.createElement("canvas");
    c.width = 700;
    c.height = 220;
    c.className = "map-canvas";
    this.container.appendChild(c);
    this._canvas = c;
    this._t0 = Date.now() / 1000;
    this._startPoll();
  }

  unmount() {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = null;
    }
    super.unmount();
  }

  _startPoll() {
    if (this._interval) clearInterval(this._interval);
    this._interval = setInterval(() => this._fetch(), 2000);
    this._fetch();
  }

  async _fetch() {
    if (this._frozen) return;
    try {
      const res = await fetch("http://localhost:9091");
      if (!res.ok) throw new Error(String(res.status));
      const procs = await res.json();
      const t = Date.now() / 1000 - this._t0;
      procs.forEach((p) => {
        const name = p.name || "proc";
        if (!this._series[name]) this._series[name] = [];
        this._series[name].push({ t, mb: p.mb });
        if (this._series[name].length > 120) this._series[name].shift();
      });
      this._render();
      this._checkFail();
    } catch (e) {
      const fail = document.getElementById("mem-fail");
      if (fail) fail.textContent = "Sin ram_monitor (localhost:9091): " + e.message;
    }
  }

  _checkFail() {
    const fail = document.getElementById("mem-fail");
    if (!fail) return;
    const names = Object.keys(this._series);
    let worst = null;
    let delta = 0;
    names.forEach((n) => {
      const s = this._series[n];
      if (s.length < 2) return;
      const d = s[s.length - 1].mb - s[0].mb;
      if (d > delta) {
        delta = d;
        worst = n;
      }
    });
    if (worst && delta > this._thresholdMb) {
      fail.textContent = `FAIL: ${worst}: +${delta.toFixed(1)}MB`;
      fail.style.display = "block";
    } else {
      fail.textContent = "";
      fail.style.display = "none";
    }
  }

  _render() {
    const c = this._canvas;
    const ctx = c.getContext("2d");
    const W = c.width;
    const H = c.height;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, W, H);
    const all = Object.values(this._series).flat();
    if (!all.length) return;
    let maxMb = 50;
    let maxT = 1;
    Object.values(this._series).forEach((s) => {
      s.forEach((p) => {
        maxMb = Math.max(maxMb, p.mb);
        maxT = Math.max(maxT, p.t);
      });
    });
    const colors = ["#4a9eff", "#00e676", "#ffab40", "#ff5252", "#ce93d8"];
    let ci = 0;
    Object.entries(this._series).forEach(([name, pts]) => {
      if (pts.length < 2) return;
      ctx.strokeStyle = colors[ci % colors.length];
      ci++;
      ctx.beginPath();
      pts.forEach((p, i) => {
        const x = (p.t / maxT) * (W - 20) + 10;
        const y = H - 10 - (p.mb / maxMb) * (H - 20);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.fillStyle = colors[ci - 1];
      ctx.font = "10px monospace";
      ctx.fillText(name, W - 200, 14 + ci * 12);
    });
    const thY = H - 10 - (this._thresholdMb / maxMb) * (H - 20);
    ctx.strokeStyle = "rgba(255,82,82,0.6)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, thY);
    ctx.lineTo(W, thY);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

window.MemoryPanel = MemoryPanel;
