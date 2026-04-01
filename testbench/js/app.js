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

  /** @type {Map<string, object>} */
  const tcResults = new Map();

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
      state.fsmState = msg;
      dispatchPanel("/fsm/state", msg);
    });
    sub("/fsm/current_mode", "std_msgs/String", (msg) => {
      state.legacyMode = msg.data;
      dispatchPanel("/fsm/current_mode", msg);
    });
    sub("/nav/quality_flag", "std_msgs/Float64", (msg) => {
      state.quality = msg.data;
      dispatchPanel("/nav/quality_flag", msg);
    });
    sub("/daidalus/alert_level", "std_msgs/Int32", (msg) => {
      state.daidalusLevel = msg.data;
      dispatchPanel("/daidalus/alert_level", msg);
    });
    sub("/fdir/emergency", "std_msgs/Bool", (msg) => {
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
    TelemetryPanel.update(state);
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

  async function runTc() {
    if (!activeTc || !bridge.connected) return;
    if (activePanel) activePanel.onTCStart(activeTc);
    setBadge(activeTc.id, "run");
    logLine(`BEGIN ${activeTc.id} ${activeTc.name || activeTc.title || ""}`);
    const def = activeTc.definition || (window.getTcDefinition && window.getTcDefinition(activeTc.id));
    const res = await runner.run(activeTc);
    const xfail = def && def.xfail ? def.xfail : null;
    let badge = res.pass ? "pass" : "fail";
    if (xfail && !res.pass) badge = "xfail";
    setBadge(activeTc.id, badge);
    logLine(`END ${activeTc.id} → ${res.pass ? "PASS" : "FAIL"} (${res.detail})`);

    const stepsTotal = res.stepsTotal != null ? res.stepsTotal : 0;
    const stepsLabel =
      stepsTotal > 0 ? `${res.stepsOk != null ? res.stepsOk : 0}/${stepsTotal} OK` : "N/A (0 pasos)";

    const payload = {
      tcId: activeTc.id,
      pass: res.pass,
      evidence: res.evidence,
      detail: res.detail,
      durationMs: res.durationMs != null ? res.durationMs : 0,
      stepsLabel,
      timestamp: formatLocalTs(),
      xfail,
    };
    tcResults.set(activeTc.id, payload);
    if (resultsPanel) resultsPanel.show(payload);
    if (activePanel) activePanel.onTCEnd(res);
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
    }
    mountPanelForActiveTc();
    wireRos();
    document.getElementById("btn-run").addEventListener("click", runTc);
    document.getElementById("btn-reset").addEventListener("click", resetBench);
    document.getElementById("btn-stop-stack").addEventListener("click", stopStackClient);
    requestAnimationFrame(tick);
  });
})();
