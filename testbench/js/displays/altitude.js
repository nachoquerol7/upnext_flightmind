/**
 * Altitude vs time from vehicle_model.state (assumes index 2 = Down in NED → alt = -down)
 */
class AltitudeProfile {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    /** @type {Array<{t:number, alt:number}>} */
    this.samples = [];
    this.maxSamples = 200;
  }

  pushFromVehicleArray(data) {
    if (!data || !data.length) return;
    const d = data[2] != null ? Number(data[2]) : 0;
    const alt = -d;
    const t = Date.now();
    this.samples.push({ t, alt });
    if (this.samples.length > this.maxSamples) this.samples.shift();
  }

  render() {
    const ctx = this.ctx;
    const W = this.canvas.width;
    const H = this.canvas.height;
    ctx.fillStyle = "#0a1628";
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#2a4a66";
    ctx.strokeRect(0, 0, W - 1, H - 1);
    if (this.samples.length < 2) {
      ctx.fillStyle = "#6a8aaa";
      ctx.font = "11px monospace";
      ctx.fillText("Altitud (esperando /vehicle_model/state)", 8, 22);
      return;
    }
    const alts = this.samples.map((s) => s.alt);
    const t0 = this.samples[0].t;
    const t1 = this.samples[this.samples.length - 1].t;
    const amin = Math.min(...alts);
    const amax = Math.max(...alts, amin + 1);
    ctx.beginPath();
    ctx.strokeStyle = "#4a9eff";
    this.samples.forEach((s, i) => {
      const x = ((s.t - t0) / Math.max(1, t1 - t0)) * (W - 20) + 10;
      const y = H - 10 - ((s.alt - amin) / (amax - amin)) * (H - 20);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = "#e0e8f0";
    ctx.font = "10px monospace";
    ctx.fillText(`alt min/max: ${amin.toFixed(1)} / ${amax.toFixed(1)} m`, 8, 14);
  }
}

window.AltitudeProfile = AltitudeProfile;
