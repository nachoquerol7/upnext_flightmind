/** M9 — E2E nominal */
(function () {
  const T = (topic, type, msg) => ({ action: "publish", topic, type, msg });
  const E = (topic, type, field, value, timeout_ms) => ({
    action: "expect",
    topic,
    type,
    field,
    value,
    timeout_ms: timeout_ms || 6000,
  });
  const W = (ms) => ({ action: "wait_ms", ms });
  const MODE = "/fsm/current_mode";
  const STR = "std_msgs/String";

  window.M9E2E = {
    id: "M9",
    title: "M9 — E2E Nominal",
    tcs: [
      {
        id: "TC-E2E-001",
        name: "Misión nominal hasta CRUISE",
        module: "M9",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(150),
          E(MODE, STR, "data", "AUTOTAXI", 5000),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(150),
          E(MODE, STR, "data", "TAKEOFF", 5000),
          T("/fsm/in/takeoff_complete", "std_msgs/Bool", { data: true }),
          W(250),
          E(MODE, STR, "data", "CRUISE", 8000),
        ],
      },
    ],
    mount(root) {
      root.innerHTML = "";
      const grid = document.createElement("div");
      grid.style.display = "grid";
      grid.style.gridTemplateColumns = "1fr 1fr";
      grid.style.gap = "10px";
      const mapWrap = document.createElement("div");
      const fsmWrap = document.createElement("div");
      const telWrap = document.createElement("div");
      telWrap.style.gridColumn = "1 / 3";
      telWrap.style.border = "1px solid #1e3a52";
      telWrap.style.borderRadius = "8px";
      telWrap.style.padding = "8px";
      telWrap.style.background = "#0a1628";
      telWrap.innerHTML =
        '<div class="section-title" style="margin-bottom:6px;">Telemetría (resumen)</div><div id="e2e-tele-mini" style="font-size:11px;color:#b8d4f0;"></div>';

      const c = document.createElement("canvas");
      c.className = "map-canvas";
      c.width = 380;
      c.height = 220;
      mapWrap.appendChild(c);
      mapWrap.appendChild(document.createElement("br"));
      const t = document.createElement("div");
      t.style.fontSize = "11px";
      t.style.color = "#8aa4bc";
      t.textContent = "Mapa E2E (sintético)";
      mapWrap.appendChild(t);

      const fsmHost = document.createElement("div");
      fsmWrap.appendChild(fsmHost);
      FsmGraph.mount(fsmHost);

      grid.appendChild(mapWrap);
      grid.appendChild(fsmWrap);
      grid.appendChild(telWrap);
      root.appendChild(grid);

      this._map = new Map2D(c);
      this._mini = document.getElementById("e2e-tele-mini");
    },
    update(st) {
      FsmGraph.update(st);
      const arr = st.vehicleState;
      if (arr && arr.length >= 3) {
        const n = Number(arr[0]);
        const e = Number(arr[1]);
        this._map.setVehicle(n, e, st.quality != null ? st.quality : 1);
      }
      this._map.render();
      if (this._mini) {
        this._mini.innerHTML = `mode=${(st.fsmState && st.fsmState.current_mode) || "—"} | q=${st.quality != null ? st.quality.toFixed(2) : "—"} | dai=${st.daidalusLevel != null ? st.daidalusLevel : "—"} | bat=100%`;
      }
    },
  };
})();
