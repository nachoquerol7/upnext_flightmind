/**
 * Dashboard compuesto M9 + M10 (fault highlight).
 */
class E2EPanel extends BasePanel {
  mount() {
    this.container.innerHTML = "";
    const root = document.createElement("div");
    root.className = "e2e-grid";
    root.innerHTML = `
      <div class="e2e-cell map" id="e2e-map-wrap"></div>
      <div class="e2e-cell fsm" id="e2e-fsm-wrap"></div>
      <div class="e2e-cell health" id="e2e-health-wrap"></div>
      <div class="e2e-cell events" id="e2e-events-wrap"></div>
    `;
    this.container.appendChild(root);
    const mapRoot = document.getElementById("e2e-map-wrap");
    const c = document.createElement("canvas");
    c.width = 320;
    c.height = 200;
    c.className = "map-canvas";
    mapRoot.appendChild(c);
    this._map = new MapPanelCanvas(c);
    this._map.waypoints = [
      { x: 40, y: 170 },
      { x: 200, y: 120 },
    ];
    this._map.setActiveRoute(this._map.waypoints);
    const fsmHost = document.getElementById("e2e-fsm-wrap");
    FsmGraph.mount(fsmHost);
    const health = document.getElementById("e2e-health-wrap");
    health.innerHTML =
      '<div class="e2e-mini-title">Salud</div><div class="e2e-health-mini" id="e2e-h-mini">—</div>';
    const ev = document.getElementById("e2e-events-wrap");
    ev.innerHTML =
      '<div class="e2e-mini-title">Hitos</div><ul class="e2e-timeline" id="e2e-tl"></ul>';
    this._timeline = [];
    this._lastMode = "";
    this._faultFlashUntil = 0;
    this._faultQuadrant = null;
  }

  syncFromState(st) {
    if (this._frozen) return;
    FsmGraph.update(st);
    const mode = (st.fsmState && st.fsmState.current_mode) || st.legacyMode || "";
    this._map.setFsmMode(mode);
    if (mode && mode !== this._lastMode) {
      this._lastMode = mode;
      this._pushEvent("FSM → " + mode);
    }
    if (st.daidalusLevel != null && st.daidalusLevel >= 2) {
      this._pushEvent("EVENT — intruso (alert ≥ MID)");
    }
    const arr = st.vehicleState;
    if (arr && arr.length >= 3) {
      const n = Number(arr[0]);
      const e = Number(arr[1]);
      this._map.setVehicle(n, e, st.quality != null ? st.quality : 1);
    }
    this._map.render();
    const mini = document.getElementById("e2e-h-mini");
    if (mini) {
      mini.textContent = `mode=${mode || "—"} | q=${st.quality != null ? st.quality.toFixed(2) : "—"} | emerg=${st.fdirEmergency ? "1" : "0"}`;
    }
    if (Date.now() < this._faultFlashUntil && this._faultQuadrant) {
      const el = document.getElementById("e2e-" + this._faultQuadrant + "-wrap");
      if (el) el.classList.add("e2e-fault-flash");
    } else {
      this.container.querySelectorAll(".e2e-fault-flash").forEach((e) => e.classList.remove("e2e-fault-flash"));
    }
  }

  onMessage(topic, msg) {
    if (this._frozen) return;
    if (topic === "/fdir/active_fault" && msg && msg.data) {
      this._pushEvent("FAULT — " + msg.data);
      this._faultFlashUntil = Date.now() + 3000;
      this._faultQuadrant = "health";
    }
  }

  _pushEvent(line) {
    const t0 = this._timeline.length ? this._timeline[0].t : Date.now();
    this._timeline.push({ t: Date.now(), line });
    if (this._timeline.length > 24) this._timeline.shift();
    const ul = document.getElementById("e2e-tl");
    if (!ul) return;
    ul.innerHTML = "";
    this._timeline.forEach((e) => {
      const sec = ((e.t - t0) / 1000).toFixed(0);
      const li = document.createElement("li");
      li.textContent = `[${sec}s] ${e.line}`;
      ul.appendChild(li);
    });
  }
}

window.E2EPanel = E2EPanel;
