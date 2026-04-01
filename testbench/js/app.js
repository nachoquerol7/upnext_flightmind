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

  /** TC ID → panel class (M1 FSM, M4 map, M5 radar, M6 watchdog, M8 latency, M9 E2E/memory, M10 faults). */
  const TC_PANEL_MAP = {
    "TC-FSM-001": "FsmGraphPanel",
    "TC-FSM-002": "FsmGraphPanel",
    "TC-FSM-003": "FsmGraphPanel",
    "TC-FSM-004": "FsmGraphPanel",
    "TC-FSM-005": "FsmGraphPanel",
    "TC-FSM-006": "FsmGraphPanel",
    "TC-FSM-007": "FsmGraphPanel",
    "TC-FSM-008": "FsmGraphPanel",
    "TC-TO-001": "FsmGraphPanel",
    "TC-LOC-001": "MapPanel",
    "TC-LOC-003": "MapPanel",
    "TC-DAI-001": "RadarPanel",
    "TC-DAI-002": "RadarPanel",
    "TC-DAI-003": "RadarPanel",
    "TC-DAI-004": "RadarPanel",
    "TC-FDIR-001": "WatchdogPanel",
    "TC-FDIR-002": "WatchdogPanel",
    "TC-FDIR-009": "WatchdogPanel",
    "TC-MW-001": "LatencyPanel",
    "TC-E2E-001": "E2EPanel",
    "TC-E2E-007": "MemoryPanel",
    "TC-FAULT-001": "E2EPanel",
    "TC-FAULT-008": "WatchdogPanel",
  };

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
    const name = TC_PANEL_MAP[tcId] || "FsmGraphPanel";
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

  const PLACEHOLDER = (id, label) => ({
    id,
    title: label,
    tcs: [],
  });

  const MODULES = [
    window.M1FSM,
    window.M2INT || PLACEHOLDER("M2", "M2 — Integrity"),
    PLACEHOLDER("M3", "M3 — Middleware"),
    window.M4LOC,
    window.M5DAI,
    window.M6FDIR,
    window.M7NAV,
    window.M8MW || PLACEHOLDER("M8", "M8 — Middleware ROS"),
    window.M9E2E,
    window.M10FLT || PLACEHOLDER("M10", "M10 — E2E Faults"),
  ];

  function getModule(mid) {
    return MODULES.find((m) => m.id === mid) || MODULES[0];
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
    sb.innerHTML = "";
    MODULES.forEach((mod) => {
      const block = document.createElement("div");
      block.className = "module-block open";
      const head = document.createElement("div");
      head.className = "module-head";
      head.innerHTML = `<span>${mod.title}</span><span class="chev">▼</span>`;
      const body = document.createElement("div");
      body.className = "module-body";
      mod.tcs.forEach((tc) => {
        const row = document.createElement("div");
        row.className = "tc-item";
        row.dataset.tcId = tc.id;
        row.innerHTML = `<span class="id">${tc.id}</span><span class="badge badge-idle" data-badge="${tc.id}">—</span>`;
        row.addEventListener("click", () => {
          document.querySelectorAll(".tc-item").forEach((el) => el.classList.remove("active"));
          row.classList.add("active");
          activeTc = tc;
          activeModuleId = mod.id;
          document.querySelectorAll(".module-block").forEach((b) => b.classList.remove("open"));
          block.classList.add("open");
          mountPanelForActiveTc();
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
    el.className = "badge " + (status === "pass" ? "badge-pass" : status === "fail" ? "badge-fail" : status === "run" ? "badge-run" : "badge-idle");
    el.textContent = status === "pass" ? "PASS" : status === "fail" ? "FAIL" : status === "run" ? "RUN" : "—";
  }

  async function runTc() {
    if (!activeTc || !bridge.connected) return;
    if (activePanel) activePanel.onTCStart(activeTc);
    setBadge(activeTc.id, "run");
    logLine(`BEGIN ${activeTc.id} ${activeTc.name}`);
    const res = await runner.run(activeTc);
    setBadge(activeTc.id, res.pass ? "pass" : "fail");
    logLine(`END ${activeTc.id} → ${res.pass ? "PASS" : "FAIL"} (${res.detail})`);
    if (activePanel) activePanel.onTCEnd(res);
  }

  function resetBench() {
    logLine("Reset testbench UI (no reinicia nodos ROS).");
    document.querySelectorAll("[data-badge]").forEach((el) => {
      el.className = "badge badge-idle";
      el.textContent = "—";
    });
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
    TelemetryPanel.mount(document.getElementById("right-panel"));
    buildSidebar();
    let firstTc = null;
    for (const m of MODULES) {
      if (m.tcs && m.tcs.length) {
        firstTc = m.tcs[0];
        activeModuleId = m.id;
        break;
      }
    }
    if (firstTc) {
      activeTc = firstTc;
      document.querySelector(`[data-badge="${firstTc.id}"]`)?.closest(".tc-item")?.classList.add("active");
    }
    mountPanelForActiveTc();
    wireRos();
    document.getElementById("btn-run").addEventListener("click", runTc);
    document.getElementById("btn-reset").addEventListener("click", resetBench);
    document.getElementById("btn-stop-stack").addEventListener("click", stopStackClient);
    requestAnimationFrame(tick);
  });
})();
