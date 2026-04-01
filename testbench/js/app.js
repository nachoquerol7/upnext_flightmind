/**
 * SIL V&V Testbench — layout, ROS subscriptions, module router, TC runner
 */
(function () {
  /** @type {RosBridge} */
  let bridge;
  /** @type {TCRunner} */
  let runner;
  let activeModuleId = "M1";
  /** @type {import('./tc_runner').TestCase | null} */
  let activeTc = null;

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

  const PLACEHOLDER = (id, label) => ({
    id,
    title: label,
    tcs: [],
    mount(root) {
      root.innerHTML = "";
      const d = document.createElement("div");
      d.className = "placeholder-box";
      d.innerHTML = `${label}<br/>Sin TCs cableados en este build.`;
      root.appendChild(d);
    },
    update() {},
  });

  const M10E2E = {
    id: "M10",
    title: "M10 — E2E Faults",
    tcs: [],
    mount(root) {
      root.innerHTML = "";
      FaultTreeDisplay.mount(root);
    },
    update() {
      FaultTreeDisplay.update();
    },
  };

  const MODULES = [
    window.M1FSM,
    PLACEHOLDER("M2", "M2 — Integrity"),
    PLACEHOLDER("M3", "M3 — Middleware"),
    window.M4LOC,
    window.M5DAI,
    window.M6FDIR,
    window.M7NAV,
    PLACEHOLDER("M8", "M8 — Middleware ROS"),
    window.M9E2E,
    M10E2E,
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
    });
    sub("/fsm/current_mode", "std_msgs/String", (msg) => {
      state.legacyMode = msg.data;
    });
    sub("/nav/quality_flag", "std_msgs/Float64", (msg) => {
      state.quality = msg.data;
    });
    sub("/daidalus/alert_level", "std_msgs/Int32", (msg) => {
      state.daidalusLevel = msg.data;
    });
    sub("/fdir/emergency", "std_msgs/Bool", (msg) => {
      state.fdirEmergency = msg.data;
    });
    sub("/fdir/status", "std_msgs/String", (msg) => {
      state.fdirStatus = msg.data;
    });
    sub("/fdir/active_fault", "std_msgs/String", (msg) => {
      if (msg.data !== state.fdirActiveFault) {
        state._fdirEvent = `${new Date().toISOString()} active_fault=${msg.data}`;
      }
      state.fdirActiveFault = msg.data;
    });
    sub("/vehicle_model/state", "std_msgs/Float64MultiArray", (msg) => {
      state.vehicleState = msg.data;
    });

    logLine("Subscriptions armed (si el tipo no coincide con tu stack, ajusta messageType en app.js).");
  }

  function refreshTelemetry() {
    TelemetryPanel.update(state);
  }

  function refreshMain() {
    const mod = getModule(activeModuleId);
    const root = document.getElementById("main-display");
    root.innerHTML = "";
    mod.mount(root);
  }

  function tick() {
    const mod = getModule(activeModuleId);
    try {
      mod.update(state);
    } catch (e) {
      console.error(e);
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
          refreshMain();
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
    setBadge(activeTc.id, "run");
    logLine(`BEGIN ${activeTc.id} ${activeTc.name}`);
    const res = await runner.run(activeTc);
    setBadge(activeTc.id, res.pass ? "pass" : "fail");
    logLine(`END ${activeTc.id} → ${res.pass ? "PASS" : "FAIL"} (${res.detail})`);
  }

  function resetBench() {
    logLine("Reset testbench UI (no reinicia nodos ROS).");
    document.querySelectorAll("[data-badge]").forEach((el) => {
      el.className = "badge badge-idle";
      el.textContent = "—";
    });
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
    activeModuleId = "M1";
    refreshMain();
    wireRos();
    document.getElementById("btn-run").addEventListener("click", runTc);
    document.getElementById("btn-reset").addEventListener("click", resetBench);
    document.getElementById("btn-stop-stack").addEventListener("click", stopStackClient);
    requestAnimationFrame(tick);
  });
})();
