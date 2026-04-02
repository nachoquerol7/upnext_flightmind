/**
 * Panel compacto: quality_flag vs umbral de histéresis (FSM / LOC).
 */
class HysteresisPanel extends BasePanel {
  mount() {
    this.container.innerHTML = "";
    const root = document.createElement("div");
    root.className = "hysteresis-panel";
    root.innerHTML = `
      <div class="hys-title">Calidad / histéresis</div>
      <div class="hys-threshold-line" title="Umbral típico 0.5 (YAML FSM)">
        <span class="hys-th-label">umbral</span>
      </div>
      <div class="hys-bar-wrap">
        <div class="hys-bar-fill" data-hys-fill></div>
      </div>
      <div class="hys-values"><span data-hys-val>—</span> <span class="hys-muted">/ 1.0</span></div>
      <div class="hys-badge" data-hys-badge>—</div>
    `;
    this.container.appendChild(root);
    this._root = root;
    this._threshold = 0.5;
    this.subscribeRos("/nav/quality_flag", "std_msgs/Float64", (msg) => this._applyQuality(msg.data));
  }

  handleTopic(topic, msg) {
    if (topic === "/nav/quality_flag" && msg && msg.data != null) {
      this._applyQuality(msg.data);
    }
  }

  _applyQuality(q) {
    const v = Number(q);
    if (!Number.isFinite(v)) return;
    const fill = this._root.querySelector("[data-hys-fill]");
    const valEl = this._root.querySelector("[data-hys-val]");
    const badge = this._root.querySelector("[data-hys-badge]");
    if (valEl) valEl.textContent = v.toFixed(2);
    if (fill) {
      fill.style.width = `${Math.min(100, Math.max(0, v * 100))}%`;
      fill.classList.remove("hys-ok", "hys-warn", "hys-bad");
      if (v > this._threshold + 0.05) fill.classList.add("hys-ok");
      else if (v >= this._threshold) fill.classList.add("hys-warn");
      else fill.classList.add("hys-bad");
    }
    if (badge) {
      if (v < this._threshold) {
        badge.textContent = "DEBAJO umbral → EVENT posible";
        badge.className = "hys-badge hys-bad";
      } else {
        badge.textContent = "Por encima del umbral";
        badge.className = "hys-badge hys-ok";
      }
    }
  }

  syncFromState(st) {
    if (this._frozen) return;
    if (st.quality != null) this._applyQuality(st.quality);
  }
}

window.HysteresisPanel = HysteresisPanel;
