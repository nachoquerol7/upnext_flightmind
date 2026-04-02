/**
 * Timeline de latencia / intervalos (M8). Sin stamp ROS2: usa intervalo entre mensajes como proxy.
 */
class LatencyPanel extends BasePanel {
  constructor(container, ros) {
    super(container, ros);
    this._topics = [
      "/fsm/state",
      "/fdir/status",
      "/daidalus/alert_level",
      "/nav/quality_flag",
    ];
    this._thresholdMs = 500;
    this._samples = [];
    this._lastArrival = {};
    this._rows = {};
  }

  mount() {
    this.container.innerHTML = "";
    const head = document.createElement("div");
    head.className = "latency-head";
    head.innerHTML = `<div class="latency-p99" id="latency-p99">P99: —</div>
      <div class="latency-badge" id="latency-badge">—</div>
      <div class="latency-note">Intervalo entre llegadas (proxy; sin header stamp en bridge)</div>`;
    this.container.appendChild(head);
    const host = document.createElement("div");
    host.className = "latency-rows";
    host.id = "latency-rows";
    this._topics.forEach((t) => {
      const row = document.createElement("div");
      row.className = "latency-row";
      row.dataset.topic = t;
      row.innerHTML = `<span class="latency-topic"></span>
        <div class="latency-track"><div class="latency-bar"></div><div class="latency-threshold"></div></div>
        <span class="latency-val"></span>`;
      row.querySelector(".latency-topic").textContent = t;
      host.appendChild(row);
      this._rows[t] = row;
    });
    this.container.appendChild(host);
    const chart = document.createElement("canvas");
    chart.width = 640;
    chart.height = 120;
    chart.className = "map-canvas";
    chart.id = "latency-chart";
    this.container.appendChild(chart);
    this._chart = chart;
    this._hist = [];
  }

  handleTopic(topic, msg) {
    const now = performance.now();
    const prev = this._lastArrival[topic];
    this._lastArrival[topic] = now;
    if (prev == null) return;
    const delta = now - prev;
    this._samples.push(delta);
    if (this._samples.length > 200) this._samples.shift();
    const row = this._rows[topic];
    if (row) {
      const bar = row.querySelector(".latency-bar");
      const val = row.querySelector(".latency-val");
      const w = Math.min(100, (delta / (this._thresholdMs * 2)) * 100);
      if (bar) {
        bar.style.width = w + "%";
        bar.classList.toggle("latency-bad", delta > this._thresholdMs);
      }
      if (val) val.textContent = delta.toFixed(1) + " ms";
    }
  }

  syncFromState() {
    if (this._frozen) return;
    const arr = this._samples.slice().sort((a, b) => a - b);
    const p99 = arr.length ? arr[Math.floor(arr.length * 0.99)] || arr[arr.length - 1] : 0;
    const p99el = document.getElementById("latency-p99");
    const badge = document.getElementById("latency-badge");
    if (p99el) p99el.textContent = "P99: " + (arr.length ? p99.toFixed(1) : "—") + " ms";
    if (badge) {
      const pass = arr.length && p99 < this._thresholdMs;
      badge.textContent = arr.length ? (pass ? "PASS" : "FAIL") : "—";
      badge.className = "latency-badge " + (pass ? "lat-pass" : "lat-fail");
      if (arr.length && !pass) {
        badge.textContent = `P99: ${p99.toFixed(0)}ms vs límite ${this._thresholdMs}ms`;
      }
    }
    this._hist.push(p99);
    if (this._hist.length > 60) this._hist.shift();
    this._drawChart();
  }

  _drawChart() {
    const c = this._chart;
    if (!c) return;
    const ctx = c.getContext("2d");
    const W = c.width;
    const H = c.height;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, W, H);
    const max = Math.max(this._thresholdMs * 2, ...this._hist, 1);
    ctx.strokeStyle = "#ff5252";
    ctx.beginPath();
    const y0 = H - (this._thresholdMs / max) * (H - 6);
    ctx.moveTo(0, y0);
    ctx.lineTo(W, y0);
    ctx.stroke();
    if (this._hist.length < 2) return;
    ctx.strokeStyle = "#4a9eff";
    ctx.beginPath();
    this._hist.forEach((v, i) => {
      const x = (i / (this._hist.length - 1)) * W;
      const y = H - (v / max) * (H - 6);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}

window.LatencyPanel = LatencyPanel;
