/**
 * FSM graph + meta + barras de timeout por estado (M1, M2).
 */
class FsmGraphPanel extends BasePanel {
  mount() {
    this.container.innerHTML = "";
    const box = document.createElement("div");
    box.className = "panel-fsm-wrap";
    FsmGraph.mount(box);
    const barHost = document.createElement("div");
    barHost.className = "fsm-timeout-bars";
    barHost.id = "fsm-timeout-bars";
    box.appendChild(barHost);
    this.container.appendChild(box);
    this._barHost = barHost;
    this._modeEnterAt = Date.now();
    this._lastMode = "";
    this._timeoutSec = 0;
    this._buildTimeoutBars();
  }

  onTCStart(tc) {
    super.onTCStart(tc);
    this._timeoutSec = (tc && tc.max_duration_sec) || 0;
    this._buildTimeoutBars();
  }

  _buildTimeoutBars() {
    if (!this._barHost) return;
    this._barHost.innerHTML = "";
    if (!this._timeoutSec) {
      this._barHost.style.display = "none";
      return;
    }
    this._barHost.style.display = "block";
    const nodes = [
      "PREFLIGHT",
      "AUTOTAXI",
      "TAKEOFF",
      "CRUISE",
      "EVENT",
      "LANDING",
      "GO_AROUND",
      "RTB",
      "ABORT",
    ];
    nodes.forEach((id) => {
      const row = document.createElement("div");
      row.className = "fsm-timeout-row";
      row.dataset.node = id;
      row.innerHTML = `<span class="fsm-timeout-label">${id}</span><div class="fsm-timeout-track"><div class="fsm-timeout-fill"></div></div>`;
      this._barHost.appendChild(row);
    });
  }

  syncFromState(st) {
    if (this._frozen) return;
    const mode = (st.fsmState && st.fsmState.current_mode) || st.legacyMode || "";
    if (mode && mode !== this._lastMode) {
      this._lastMode = mode;
      this._modeEnterAt = Date.now();
    }
    FsmGraph.update(st);
    this._updateTimeoutBars(mode);
  }

  _updateTimeoutBars(activeMode) {
    if (!this._timeoutSec || !this._barHost) return;
    const maxMs = this._timeoutSec * 1000;
    const now = Date.now();
    const inStateMs = now - this._modeEnterAt;
    this._barHost.querySelectorAll(".fsm-timeout-row").forEach((row) => {
      const id = row.dataset.node;
      const fill = row.querySelector(".fsm-timeout-fill");
      if (!fill) return;
      if (id !== activeMode) {
        fill.style.width = "0%";
        fill.classList.remove("fsm-timeout-over");
        return;
      }
      const pct = Math.min(100, (inStateMs / maxMs) * 100);
      fill.style.width = pct + "%";
      fill.classList.toggle("fsm-timeout-over", inStateMs >= maxMs);
    });
  }
}

window.FsmGraphPanel = FsmGraphPanel;
