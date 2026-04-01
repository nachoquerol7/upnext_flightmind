/**
 * Right panel: live signal bars (reads global __TB_STATE)
 */
const TelemetryPanel = {
  mount(root) {
    this.root = root;
    this.root.innerHTML = `
      <h2 class="section-title">Señales en tiempo real</h2>
      <div class="signal-row"><div class="label">/fsm/state → current_mode</div><div class="val" id="sig-mode">—</div></div>
      <div class="signal-row"><div class="label">active_trigger</div><div class="val" id="sig-trig">—</div></div>
      <div class="signal-row"><div class="label">event_substate</div><div class="val" id="sig-sub">—</div></div>
      <div class="signal-row"><div class="label">/nav/quality_flag</div><div class="val" id="sig-q">—</div><div class="telemetry-bar"><div id="bar-q" style="width:0%; background:#00e676"></div></div></div>
      <div class="signal-row"><div class="label">/daidalus/alert_level</div><div class="val" id="sig-dai">—</div><div class="telemetry-bar"><div id="bar-dai" style="width:0%; background:#ffab40"></div></div></div>
      <div class="signal-row"><div class="label">/fdir/emergency</div><div class="val" id="sig-em">—</div></div>
      <div class="signal-row"><div class="label">/fdir/status</div><div class="val" id="sig-fs">—</div></div>
      <div class="signal-row"><div class="label">/fdir/active_fault</div><div class="val" id="sig-fa">—</div></div>
    `;
  },
  update(st) {
    if (!this.root) return;
    const fsm = st.fsmState || {};
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = v == null ? "—" : String(v);
    };
    set("sig-mode", fsm.current_mode);
    set("sig-trig", fsm.active_trigger);
    set("sig-sub", fsm.event_substate);
    const q = st.quality != null ? st.quality : null;
    set("sig-q", q != null ? q.toFixed(3) : "—");
    const bq = document.getElementById("bar-q");
    if (bq && q != null) {
      bq.style.width = Math.max(0, Math.min(100, q * 100)) + "%";
      bq.style.background = q < 0.5 ? "#ff5252" : q < 0.8 ? "#ffab40" : "#00e676";
    }
    const dai = st.daidalusLevel;
    set("sig-dai", dai != null ? String(dai) : "—");
    const bd = document.getElementById("bar-dai");
    if (bd && dai != null) {
      bd.style.width = Math.min(100, dai * 25) + "%";
    }
    set("sig-em", st.fdirEmergency);
    set("sig-fs", st.fdirStatus);
    set("sig-fa", st.fdirActiveFault);
  },
};

window.TelemetryPanel = TelemetryPanel;
