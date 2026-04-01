/**
 * SIL V&V Testbench — paneles por TC, ROS, TC runner
 */
(function () {
  /** @type {RosBridge} */
  let bridge;
  /** @type {TCRunner} */
  let runner;
  let activeModuleId = "M1";
  /** @type {import('./tc_runner').TestCase | null} */
  let activeTc = null;
  /** @type {BasePanel | null} */
  let activePanel = null;
  /** @type {TCDescriptionPanel | null} */
  let tcDescPanel = null;
  /** @type {ResultsPanel | null} */
  let resultsPanel = null;
  /** @type {LLMAnalyst | null} */
  let llmAnalyst = null;

  /** @type {Map<string, object>} */
  const tcResults = new Map();

  /** @type {Record<string, number>} */
  const topicLastMsg = {};

  const state = {
    fsmState: {},
    legacyMode: "",
    quality: null,
    daidalusLevel: null,
    fdirEmergency: null,
    fdirStatus: "",
    fdirActiveFault: "",
    vehicleState: null,
    _fdirEvent: null,
  };

  function getModules() {
    if (typeof window.getModulesForSidebar !== "function") {
      console.warn("getModulesForSidebar missing; load tc_definitions.js");
      return [];
    }
    return window.getModulesForSidebar();
  }

  function logLine(text) {
    const log = document.getElementById("log");
    if (!log) return;
    const div = document.createElement("div");
    div.className = "log-line";
    const ts = new Date().toISOString().split("T")[1].replace("Z", "");
    div.innerHTML = `<span class="ts">${ts}</span>${escapeHtml(text)}`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function panelClassForTcId(tcId) {
    const def = window.getTcDefinition && window.getTcDefinition(tcId);
    const name = (def && def.panel) || "FsmGraphPanel";
    const Ctor = window[name];
    return Ctor || window.FsmGraphPanel;
  }

  function mountPanelForActiveTc() {
    const root = document.getElementById("main-display");
    if (!root) return;
    if (activePanel) {
      try {
        activePanel.unmount();
      } catch (e) {
        console.error(e);
      }
      activePanel = null;
    }
    root.innerHTML = "";
    const tcId = activeTc ? activeTc.id : null;
    const Ctor = panelClassForTcId(tcId || "TC-FSM-001");
    activePanel = new Ctor(root, bridge);
    activePanel.mount();
    activePanel.onTCStart(activeTc);
    activePanel.syncFromState(state);
  }

  function getModule(mid) {
    return getModules().find((m) => m.id === mid) || getModules()[0];
  }

  function setConnUi(connected) {
    const el = document.getElementById("conn-status");
    if (!el) return;
    el.classList.toggle("connected", connected);
    el.querySelector("span.txt").textContent = connected ? "ROS2 connected" : "ROS2 disconnected";
    document.querySelectorAll("[data-requires-ros]").forEach((b) => {
      b.disabled = !connected;
    });
  }

  let _subsArmed = false;
  let _prevFsmMode = "";

  function wireRos() {
    bridge = new RosBridge("ws://localhost:9090");
    runner = new TCRunner(bridge, logLine);
    bridge.on_status((s) => {
      logLine("rosbridge: " + s);
      setConnUi(bridge.connected);
      if (s === "connected" && !_subsArmed) {
        subscribeAll();
        _subsArmed = true;
      }
    });
    bridge.connect();
  }

  function dispatchPanel(topic, msg) {
    if (activePanel && typeof activePanel.onMessage === "function") {
      try {
        activePanel.onMessage(topic, msg);
      } catch (e) {
        console.error(e);
      }
    }
  }

  function subscribeAll() {
    if (!bridge || !bridge.ros) return;
    const sub = (name, type, fn) => {
      try {
        bridge.subscribe(name, type, fn);
      } catch (e) {
        logLine("subscribe fail " + name + ": " + e);
      }
    };

    sub("/fsm/state", "flightmind_msgs/FSMState", (msg) => {
      markTopicRx("/fsm/state");
      const nm = msg.current_mode || "";
      const trigger = msg.active_trigger || "";
      if (
        llmAnalyst &&
        llmAnalyst.enabled &&
        activeTc &&
        _prevFsmMode &&
        nm !== _prevFsmMode
      ) {
        const def = activeTc.definition || (window.getTcDefinition && window.getTcDefinition(activeTc.id));
        llmAnalyst.analyze(
          `TC ${activeTc.id} en ejecución.
Transición FSM detectada: ${_prevFsmMode} → ${nm} (trigger: ${trigger}, tiempo: observado en vivo).
Oráculo esperaba: ${def ? def.oracle : "—"}.
Veredicto automático: (evaluación en curso en el panel de resultados).
¿Es correcto este comportamiento? ¿Hay algo que destacar?`,
        );
      }
      _prevFsmMode = nm;
      state.fsmState = msg;
      dispatchPanel("/fsm/state", msg);
    });
    sub("/fsm/current_mode", "std_msgs/String", (msg) => {
      markTopicRx("/fsm/current_mode");
      state.legacyMode = msg.data;
      dispatchPanel("/fsm/current_mode", msg);
    });
    sub("/nav/quality_flag", "std_msgs/Float64", (msg) => {
      markTopicRx("/nav/quality_flag");
      state.quality = msg.data;
      dispatchPanel("/nav/quality_flag", msg);
    });
    sub("/daidalus/alert_level", "std_msgs/Int32", (msg) => {
      markTopicRx("/daidalus/alert_level");
      state.daidalusLevel = msg.data;
      dispatchPanel("/daidalus/alert_level", msg);
    });
    sub("/fdir/emergency", "std_msgs/Bool", (msg) => {
      markTopicRx("/fdir/emergency");
      state.fdirEmergency = msg.data;
      dispatchPanel("/fdir/emergency", msg);
    });
    sub("/fdir/status", "std_msgs/String", (msg) => {
      state.fdirStatus = msg.data;
      dispatchPanel("/fdir/status", msg);
    });
    sub("/fdir/active_fault", "std_msgs/String", (msg) => {
      if (msg.data !== state.fdirActiveFault) {
        state._fdirEvent = `${new Date().toISOString()} active_fault=${msg.data}`;
      }
      state.fdirActiveFault = msg.data;
      dispatchPanel("/fdir/active_fault", msg);
    });
    sub("/vehicle_model/state", "std_msgs/Float64MultiArray", (msg) => {
      state.vehicleState = msg.data;
      dispatchPanel("/vehicle_model/state", msg);
    });

    logLine("Subscriptions armed (si el tipo no coincide con tu stack, ajusta messageType en app.js).");
  }

  function refreshTelemetry() {
    TelemetryPanel.update(state, hzMapFromTopics());
  }

  function tick() {
    if (activePanel && typeof activePanel.syncFromState === "function") {
      try {
        activePanel.syncFromState(state);
      } catch (e) {
        console.error(e);
      }
    }
    refreshTelemetry();
    state._fdirEvent = null;
    requestAnimationFrame(tick);
  }

  function buildSidebar() {
    const sb = document.getElementById("sidebar-body");
    if (!sb) return;
    sb.innerHTML = "";
    const MODULES = getModules();
    MODULES.forEach((mod) => {
      const block = document.createElement("div");
      block.className = "module-block open";
      const head = document.createElement("div");
      head.className = "module-head";
      head.innerHTML = `<span>${escapeHtml(mod.title)}</span><span class="chev">▼</span>`;
      const body = document.createElement("div");
      body.className = "module-body";
      mod.tcs.forEach((tc) => {
        const row = document.createElement("div");
        row.className = "tc-item";
        row.dataset.tcId = tc.id;
        row.innerHTML = `<span class="id">${escapeHtml(tc.id)}</span><span class="badge badge-idle" data-badge="${tc.id}">—</span>`;
        row.addEventListener("click", () => {
          document.querySelectorAll(".tc-item").forEach((el) => el.classList.remove("active"));
          row.classList.add("active");
          activeTc = tc;
          activeModuleId = mod.id;
          document.querySelectorAll(".module-block").forEach((b) => b.classList.remove("open"));
          block.classList.add("open");
          mountPanelForActiveTc();
          if (tcDescPanel) tcDescPanel.show(tc);
          TelemetryPanel.updateTcSummary(tc);
          const last = tcResults.get(tc.id);
          if (last && resultsPanel) resultsPanel.show(last);
          else if (resultsPanel) resultsPanel.clear();
        });
        body.appendChild(row);
      });
      if (mod.tcs.length === 0) {
        const em = document.createElement("div");
        em.style.color = "#6a8aaa";
        em.style.padding = "6px 8px";
        em.textContent = "(sin TCs)";
        body.appendChild(em);
      }
      head.addEventListener("click", () => {
        block.classList.toggle("open");
      });
      block.appendChild(head);
      block.appendChild(body);
      sb.appendChild(block);
    });
  }

  function setBadge(tcId, status) {
    const el = document.querySelector(`[data-badge="${tcId}"]`);
    if (!el) return;
    const map = {
      pass: ["badge-pass", "PASS"],
      fail: ["badge-fail", "FAIL"],
      run: ["badge-run", "RUN"],
      idle: ["badge-idle", "—"],
      xfail: ["badge-xfail", "XFAIL"],
    };
    const [cls, text] = map[status] || map.idle;
    el.className = "badge " + cls;
    el.textContent = text;
  }

  function formatLocalTs() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  function tcDef(id) {
    return window.getTcDefinition && window.getTcDefinition(id);
  }

  /**
   * @param {{ id: string, definition?: object }} tc
   * @param {{ pass: boolean, evidence?: string, detail?: string, durationMs?: number, stepsOk?: number, stepsTotal?: number }} res
   */
  function applyRunResult(tc, res, showInResultsPanel) {
    const def = tc.definition || tcDef(tc.id);
    const xfail = def && def.xfail ? def.xfail : null;
    let badge = res.pass ? "pass" : "fail";
    if (xfail && !res.pass) badge = "xfail";
    setBadge(tc.id, badge);
    const stepsTotal = res.stepsTotal != null ? res.stepsTotal : 0;
    const stepsLabel =
      stepsTotal > 0 ? `${res.stepsOk != null ? res.stepsOk : 0}/${stepsTotal} OK` : "N/A (0 pasos)";
    const payload = {
      tcId: tc.id,
      pass: res.pass,
      evidence: res.evidence,
      detail: res.detail,
      durationMs: res.durationMs != null ? res.durationMs : 0,
      stepsLabel,
      timestamp: formatLocalTs(),
      xfail,
    };
    tcResults.set(tc.id, payload);
    if (showInResultsPanel && resultsPanel && activeTc && tc.id === activeTc.id) {
      resultsPanel.show(payload);
    }
    return { def, payload };
  }

  let executionBusy = false;

  async function runTc() {
    if (!activeTc || !bridge.connected || executionBusy) return;
    executionBusy = true;
    try {
      if (activePanel) activePanel.onTCStart(activeTc);
      setBadge(activeTc.id, "run");
      logLine(`BEGIN ${activeTc.id} ${activeTc.name || activeTc.title || ""}`);
      const res = await runner.run(activeTc);
      logLine(`END ${activeTc.id} → ${res.pass ? "PASS" : "FAIL"} (${res.detail})`);
      const { def } = applyRunResult(activeTc, res, true);
      if (activePanel) activePanel.onTCEnd(res);

      if (llmAnalyst && llmAnalyst.enabled) {
        const verdict = res.pass ? "PASS" : "FAIL";
        if (!res.pass) {
          await llmAnalyst.analyze(
            `TC ${activeTc.id} ha FALLADO.
Esperado: ${def ? def.oracle : "—"}.
Recibido / detalle: ${res.detail || res.evidence || "—"}.
Gap relacionado: ${def && def.xfail ? def.xfail : "ninguno conocido"}.
¿Cuál es la causa más probable y cómo se solucionaría?`,
          );
        } else {
          await llmAnalyst.analyze(
            `TC ${activeTc.id} ha terminado con ${verdict}.
Evidencia: ${res.evidence || res.detail || "—"}.
Oráculo: ${def ? def.oracle : "—"}.
¿El comportamiento observado es coherente con un sistema nominal?`,
          );
        }
        if (activeTc.id.startsWith("TC-FAULT")) {
          await llmAnalyst.analyze(
            `Inyección de fallo en TC ${activeTc.id}.
Estado del sistema: FSM=${state.fsmState && state.fsmState.current_mode}, QF=${state.quality}, alerts DAA=${state.daidalusLevel}, FDIR emergencia=${state.fdirEmergency}.
Respuesta del runner: ${verdict}. Detalle: ${res.detail || "—"}.
¿El sistema ha respondido correctamente según los requisitos SR-FDIR-01?`,
          );
        }
      }
    } finally {
      executionBusy = false;
    }
  }

  function groupResultsByModule() {
    /** @type {Record<string, object[]>} */
    const out = {};
    for (const [id, row] of tcResults) {
      const d = tcDef(id);
      const m = (d && d.module) || "UNK";
      if (!out[m]) out[m] = [];
      out[m].push({ id, ...row });
    }
    return out;
  }

  function exportResults() {
    const defs = window.TC_DEFINITIONS || {};
    const totalDefs = Object.keys(defs).length;
    const report = {
      timestamp: new Date().toISOString(),
      stack: "FlightMind v1.0",
      summary: {
        total: tcResults.size,
        passed: 0,
        failed: 0,
        xfailed: 0,
        not_run: Math.max(0, totalDefs - tcResults.size),
      },
      modules: groupResultsByModule(),
      details: Object.fromEntries(tcResults),
    };
    for (const p of tcResults.values()) {
      if (p.pass) report.summary.passed += 1;
      else if (p.xfail) report.summary.xfailed += 1;
      else report.summary.failed += 1;
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `flightmind_vnv_results_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    logLine("Export JSON: flightmind_vnv_results_*.json");
  }

  async function runAllModule() {
    if (!bridge.connected || executionBusy) return;
    const mod = getModule(activeModuleId);
    if (!mod || !mod.tcs.length) return;
    executionBusy = true;
    let passed = 0;
    let failed = 0;
    let xfailed = 0;
    const total = mod.tcs.length;
    try {
      for (let i = 0; i < mod.tcs.length; i++) {
        const tc = mod.tcs[i];
        const idx = i + 1;
        setBadge(tc.id, "run");
        logLine(`Executing ${mod.id}... [${idx}/${total}] ${tc.id}`);
        if (activePanel && tc.id === activeTc.id) activePanel.onTCStart(tc);
        const res = await runner.run(tc);
        const def = tc.definition || tcDef(tc.id);
        const isXfail = Boolean(def && def.xfail && !res.pass);
        const verdict = res.pass ? "PASS" : isXfail ? "XFAIL" : "FAIL";
        if (res.pass) passed += 1;
        else if (isXfail) xfailed += 1;
        else failed += 1;
        applyRunResult(tc, res, true);
        logLine(`Executing ${mod.id}... [${idx}/${total}] ${tc.id} ${verdict} (${Math.round(res.durationMs || 0)}ms)`);
        if (activePanel && tc.id === activeTc.id) activePanel.onTCEnd(res);
        await new Promise((r) => setTimeout(r, 500));
      }
    } finally {
      executionBusy = false;
    }
    if (llmAnalyst && llmAnalyst.enabled) {
      await llmAnalyst.analyze(
        `Módulo ${mod.title} completado: ${passed} passed, ${xfailed} xfailed, ${failed} failed.
Gaps arquitecturales abiertos relacionados: ARCH-1.2, ARCH-1.7.
Dame un resumen ejecutivo de 2 frases del estado de este subsistema.`,
      );
    }
  }

  function resetBench() {
    logLine("Reset testbench UI (no reinicia nodos ROS).");
    document.querySelectorAll("[data-badge]").forEach((el) => {
      el.className = "badge badge-idle";
      el.textContent = "—";
    });
    tcResults.clear();
    if (resultsPanel) resultsPanel.clear();
    if (activePanel && typeof activePanel.clearVerdict === "function") {
      activePanel.clearVerdict();
      activePanel.onTCStart(activeTc);
    }
  }

  function stopStackClient() {
    if (!bridge) return;
    bridge.disconnect();
    logLine("Cliente WebSocket desconectado (Stop stack). Recarga la página para volver a conectar.");
    setConnUi(false);
  }

  document.addEventListener("DOMContentLoaded", () => {
    window.testbenchLog = logLine;
    window.tcResults = tcResults;

    TelemetryPanel.mount(document.getElementById("right-panel"));

    llmAnalyst = new window.LLMAnalyst();
    const llmOut = document.getElementById("llm-output");
    const llmHist = document.getElementById("llm-history");
    llmAnalyst.bindUi(llmOut, llmHist);

    function syncLlmKeyUi() {
      const hasKey = !!(llmAnalyst && llmAnalyst.loadKeyFromStorage());
      const sec = document.getElementById("llm-key-section");
      if (sec) sec.style.display = hasKey ? "none" : "block";
    }
    syncLlmKeyUi();
    document.getElementById("llm-save-key")?.addEventListener("click", () => {
      const inp = document.getElementById("llm-api-key");
      if (inp && llmAnalyst) llmAnalyst.setApiKey(inp.value);
      syncLlmKeyUi();
    });
    document.getElementById("llm-toggle")?.addEventListener("change", (e) => {
      if (llmAnalyst) llmAnalyst.setEnabled(/** @type {HTMLInputElement} */ (e.target).checked);
    });

    const tcHost = document.getElementById("tc-description-host");
    const resHost = document.getElementById("results-host");
    tcDescPanel = new window.TCDescriptionPanel(tcHost);
    resultsPanel = new window.ResultsPanel(resHost);
    tcDescPanel.mount();
    resultsPanel.mount();

    buildSidebar();
    let firstTc = null;
    for (const m of getModules()) {
      if (m.tcs && m.tcs.length) {
        firstTc = m.tcs[0];
        activeModuleId = m.id;
        break;
      }
    }
    if (firstTc) {
      activeTc = firstTc;
      document.querySelector(`[data-badge="${firstTc.id}"]`)?.closest(".tc-item")?.classList.add("active");
      tcDescPanel.show(firstTc);
      TelemetryPanel.updateTcSummary(firstTc);
    }
    mountPanelForActiveTc();
    wireRos();
    document.getElementById("btn-run").addEventListener("click", runTc);
    document.getElementById("btn-run-all")?.addEventListener("click", runAllModule);
    document.getElementById("btn-export")?.addEventListener("click", exportResults);
    document.getElementById("btn-reset").addEventListener("click", resetBench);
    document.getElementById("btn-stop-stack").addEventListener("click", stopStackClient);
    requestAnimationFrame(tick);
  });
})();
