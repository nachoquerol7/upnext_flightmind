/**
 * Panel derecho: señales live + resumen TC activo + analista LLM.
 */
const TelemetryPanel = {
  mount(root) {
    this.root = root;
    this.root.innerHTML = `
      <div class="right-panel-stack">
        <section class="rp-section" aria-label="Señales en tiempo real">
          <h2 class="section-title">Señales en tiempo real</h2>
          <div class="signal-row"><div class="label">/fsm/state → current_mode <span class="hz-badge" data-hz="/fsm/state">— Hz</span></div><div class="val sig-fsm-mode">—</div></div>
          <div class="signal-row"><div class="label">active_trigger</div><div class="val sig-trig">—</div></div>
          <div class="signal-row"><div class="label">event_substate</div><div class="val sig-sub">—</div></div>
          <div class="signal-row"><div class="label">/nav/quality_flag <span class="hz-badge" data-hz="/nav/quality_flag">— Hz</span></div><div class="val sig-q">—</div><div class="telemetry-bar"><div class="bar-q" style="width:0%; background:#00e676"></div></div></div>
          <div class="signal-row"><div class="label">/daidalus/alert_level <span class="hz-badge" data-hz="/daidalus/alert_level">— Hz</span></div><div class="val sig-dai">—</div><div class="telemetry-bar"><div class="bar-dai" style="width:0%; background:#ffab40"></div></div></div>
          <div class="signal-row"><div class="label">/fdir/emergency <span class="hz-badge" data-hz="/fdir/emergency">— Hz</span></div><div class="val sig-em">—</div><div class="traffic traffic-em" title="Semáforo emergencia"></div></div>
          <div class="signal-row"><div class="label">/fdir/status</div><div class="val sig-fs">—</div></div>
          <div class="signal-row"><div class="label">/fdir/active_fault</div><div class="val sig-fa">—</div></div>
        </section>

        <section class="rp-section rp-tc-active" aria-label="TC activo">
          <h2 class="section-title">TC activo</h2>
          <div id="rp-tc-body"><p class="hint">Selecciona un TC en el sidebar.</p></div>
        </section>

        <section class="rp-section rp-llm" aria-label="Analista IA">
          <div class="llm-panel">
            <div class="llm-header">
              <span class="llm-title">Analista IA</span>
              <label class="llm-toggle-wrap">
                <input type="checkbox" id="llm-toggle" />
                <span>Activar</span>
              </label>
            </div>
            <div class="llm-key-input" id="llm-key-section">
              <input type="password" placeholder="Anthropic API key" id="llm-api-key" autocomplete="off" />
              <button type="button" id="llm-save-key">Guardar</button>
              <p class="hint">La clave se guarda solo en localStorage. No sale del navegador salvo a la API Anthropic si activas el analista.</p>
            </div>
            <div class="llm-output" id="llm-output">
              <p class="placeholder">Activa el analista y ejecuta un TC para ver análisis en tiempo real.</p>
            </div>
            <div class="llm-history-wrap">
              <div class="llm-history-title">Últimos análisis</div>
              <div class="llm-history" id="llm-history"><p class="hint">Sin análisis recientes.</p></div>
            </div>
          </div>
        </section>
      </div>
    `;
  },

  /**
   * @param {object} st
   * @param {Record<string, number>} [hzByTopic] frecuencia estimada Hz
   */
  update(st, hzByTopic) {
    if (!this.root) return;
    const fsm = st.fsmState || {};
    const setCls = (sel, v) => {
      const el = this.root.querySelector(sel);
      if (el) el.textContent = v == null ? "—" : String(v);
    };
    setCls(".sig-fsm-mode", fsm.current_mode);
    setCls(".sig-trig", fsm.active_trigger);
    setCls(".sig-sub", fsm.event_substate);
    const q = st.quality != null ? st.quality : null;
    setCls(".sig-q", q != null ? q.toFixed(3) : "—");
    const bq = this.root.querySelector(".bar-q");
    if (bq && q != null) {
      bq.style.width = Math.max(0, Math.min(100, q * 100)) + "%";
      bq.style.background = q < 0.5 ? "#ff5252" : q < 0.8 ? "#ffab40" : "#00e676";
    }
    const dai = st.daidalusLevel;
    const sigDai = this.root.querySelector(".sig-dai");
    if (sigDai) {
      sigDai.textContent = dai != null ? String(dai) : "—";
      sigDai.className = "val sig-dai dai-badge lvl-" + (dai != null ? String(Math.min(3, Math.max(0, dai))) : "x");
    }
    const bd = this.root.querySelector(".bar-dai");
    if (bd && dai != null) {
      bd.style.width = Math.min(100, dai * 25) + "%";
    }
    setCls(".sig-em", st.fdirEmergency);
    const traffic = this.root.querySelector(".traffic-em");
    if (traffic) {
      traffic.className = "traffic traffic-em " + (st.fdirEmergency ? "tr-red" : "tr-green");
    }
    setCls(".sig-fs", st.fdirStatus);
    setCls(".sig-fa", st.fdirActiveFault);

    if (hzByTopic) {
      this.root.querySelectorAll(".hz-badge").forEach((el) => {
        const topic = el.getAttribute("data-hz");
        const hz = topic && hzByTopic[topic];
        el.textContent = hz != null && hz >= 0 ? `${hz.toFixed(1)} Hz` : "— Hz";
      });
    }
  },

  /**
   * @param {{ id: string, name?: string, title?: string, definition?: object } | null} tc
   */
  updateTcSummary(tc) {
    const el = document.getElementById("rp-tc-body");
    if (!el) return;
    if (!tc) {
      el.innerHTML = '<p class="hint">Selecciona un TC en el sidebar.</p>';
      return;
    }
    const d = tc.definition || (window.getTcDefinition && window.getTcDefinition(tc.id));
    const title = (d && d.title) || tc.name || tc.title || tc.id;
    const oracle = (d && d.oracle) || "—";
    const what = (d && d.what) || "—";
    const passV = d ? d.pass_visual || "—" : "—";
    const failV = d ? d.fail_visual || "—" : "—";
    el.innerHTML = `
      <div class="rp-tc-id">${escapeHtml(tc.id)}</div>
      <div class="rp-tc-title">${escapeHtml(title)}</div>
      <p class="rp-tc-label">Qué se prueba</p>
      <p class="rp-tc-text">${escapeHtml(what)}</p>
      <p class="rp-tc-label">Oráculo</p>
      <p class="rp-tc-text">${escapeHtml(oracle)}</p>
      <p class="rp-tc-label">PASS / FAIL (visual)</p>
      <p class="rp-tc-text"><strong>PASS:</strong> ${escapeHtml(passV)}<br/><strong>FAIL:</strong> ${escapeHtml(failV)}</p>
    `;
  },
};

function escapeHtml(s) {
  if (s == null) return "";
  const d = document.createElement("div");
  d.textContent = String(s);
  return d.innerHTML;
}

window.TelemetryPanel = TelemetryPanel;
