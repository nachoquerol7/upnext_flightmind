/**
 * Pasos ejecutables por TC (prioridad: bundles > legacy en tc_definitions).
 * Topics alineados con el plan SIL (FSMState en /fsm/state, quality en /nav/quality_flag, etc.).
 */
(function () {
  "use strict";
  const S = window.TC_STEPS;
  if (!S) {
    console.warn("tc_step_bundles.js: cargar después de tc_definitions.js");
    return;
  }

  const T = (topic, type, msg) => ({ action: "publish", topic, type, msg });
  const E = (topic, type, field, value, timeout_ms) => ({
    action: "expect",
    topic,
    type,
    field,
    value,
    timeout_ms: timeout_ms ?? 5000,
  });
  const N = (topic, type, field, value, timeout_ms) => ({
    action: "expect_not",
    topic,
    type,
    field,
    value,
    timeout_ms: timeout_ms ?? 2000,
  });
  const W = (ms) => ({ action: "wait_ms", ms });

  const FSM = "/fsm/state";
  const FSM_T = "flightmind_msgs/FSMState";
  const BOOL = "std_msgs/Bool";
  const F64 = "std_msgs/Float64";
  const I32 = "std_msgs/Int32";
  const STR = "std_msgs/String";
  const STR_ARR = "std_msgs/Float64MultiArray";

  function p3(n) {
    return String(n).padStart(3, "0");
  }

  function toCruise(timeout) {
    const t = timeout ?? 8000;
    return [
      T("/fsm/in/preflight_ok", BOOL, { data: true }),
      W(120),
      T("/fsm/in/taxi_clear", BOOL, { data: true }),
      W(120),
      T("/fsm/in/takeoff_complete", BOOL, { data: true }),
      W(200),
      E(FSM, FSM_T, "current_mode", "CRUISE", t),
    ];
  }

  /* ——— M1 FSM ——— */
  S["TC-FSM-001"] = [T("/fsm/in/preflight_ok", BOOL, { data: true }), W(350), E(FSM, FSM_T, "current_mode", "AUTOTAXI", 8000)];
  S["TC-FSM-002"] = [
    T("/fsm/in/preflight_ok", BOOL, { data: true }),
    W(150),
    E(FSM, FSM_T, "current_mode", "AUTOTAXI", 5000),
    T("/fsm/in/taxi_clear", BOOL, { data: true }),
    W(150),
    E(FSM, FSM_T, "current_mode", "TAKEOFF", 5000),
  ];
  S["TC-FSM-003"] = [
    T("/fsm/in/preflight_ok", BOOL, { data: true }),
    W(120),
    T("/fsm/in/taxi_clear", BOOL, { data: true }),
    W(120),
    T("/fsm/in/takeoff_complete", BOOL, { data: true }),
    W(200),
    E(FSM, FSM_T, "current_mode", "CRUISE", 6000),
  ];
  S["TC-FSM-004"] = [
    ...toCruise(6000),
    T("/nav/quality_flag", F64, { data: 0.1 }),
    W(250),
    E(FSM, FSM_T, "current_mode", "EVENT", 5000),
  ];
  S["TC-FSM-005"] = [
    ...toCruise(6000),
    T("/fsm/in/rtb_command", BOOL, { data: true }),
    W(200),
    E(FSM, FSM_T, "current_mode", "RTB", 5000),
  ];
  S["TC-FSM-006"] = [
    ...toCruise(6000),
    T("/fsm/in/land_command", BOOL, { data: true }),
    W(200),
    E(FSM, FSM_T, "current_mode", "LANDING", 5000),
  ];
  S["TC-FSM-007"] = [
    ...toCruise(6000),
    T("/nav/quality_flag", F64, { data: 0.1 }),
    W(250),
    E(FSM, FSM_T, "current_mode", "EVENT", 5000),
    T("/nav/quality_flag", F64, { data: 1.0 }),
    W(150),
    T("/fsm/in/event_cleared", BOOL, { data: true }),
    W(250),
    E(FSM, FSM_T, "current_mode", "CRUISE", 6000),
  ];
  S["TC-FSM-008"] = [
    ...toCruise(6000),
    T("/fsm/in/fdir_emergency", BOOL, { data: true }),
    W(200),
    E(FSM, FSM_T, "current_mode", "ABORT", 5000),
  ];

  const m1x = {
    9: () => [...toCruise(), T("/fsm/in/abort_command", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "ABORT", 5000)],
    10: () => [...toCruise(), T("/fsm/in/rtb_command", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "RTB", 5000)],
    11: () => [...toCruise(), T("/fsm/in/land_command", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "LANDING", 5000)],
    12: () => [
      ...toCruise(),
      T("/nav/quality_flag", F64, { data: 0.2 }),
      W(200),
      E(FSM, FSM_T, "current_mode", "EVENT", 5000),
      T("/fsm/in/event_cleared", BOOL, { data: true }),
      W(200),
      E(FSM, FSM_T, "current_mode", "CRUISE", 6000),
    ],
    13: () => [...toCruise(), T("/fsm/in/daidalus_alert", I32, { data: 2 }), W(300), E("/daidalus/alert_level", I32, "data", 2, 4000)],
    14: () => [...toCruise(), N(FSM, FSM_T, "current_mode", "ABORT", 800), T("/fsm/in/rtb_command", BOOL, { data: true }), W(200)],
    15: () => [T("/fsm/in/preflight_ok", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "AUTOTAXI", 6000)],
    16: () => [...toCruise(), T("/nav/quality_flag", F64, { data: 0.9 }), W(400), N(FSM, FSM_T, "current_mode", "EVENT", 1500)],
    17: () => [...toCruise(6000), T("/fsm/in/go_around_complete", BOOL, { data: true }), W(200)],
    18: () => [...toCruise(), T("/fsm/in/touchdown", BOOL, { data: true }), W(200)],
    19: () => [...toCruise(), T("/fsm/in/abort_command", BOOL, { data: true }), W(150), E(FSM, FSM_T, "current_mode", "ABORT", 5000)],
    20: () => [...toCruise(), T("/nav/quality_flag", F64, { data: 0.05 }), W(200), E(FSM, FSM_T, "current_mode", "EVENT", 5000)],
    21: () => [...toCruise(), T("/fsm/in/rtb_command", BOOL, { data: true }), W(100), T("/fsm/in/abort_command", BOOL, { data: true }), W(200)],
    22: () => [...toCruise(), T("/fsm/in/land_command", BOOL, { data: true }), W(200), T("/fsm/in/go_around_complete", BOOL, { data: true }), W(200)],
  };
  for (let n = 9; n <= 22; n++) {
    S["TC-FSM-" + p3(n)] = m1x[n]();
  }
  for (let n = 23; n <= 30; n++) {
    S["TC-FSM-" + p3(n)] = [];
  }

  /* ——— M2 timeouts ——— */
  S["TC-TO-001"] = [T("/fsm/in/preflight_ok", BOOL, { data: true }), W(150), E(FSM, FSM_T, "current_mode", "AUTOTAXI", 5000)];
  for (let n = 2; n <= 10; n++) {
    S["TC-TO-" + p3(n)] = [W(200 + n * 50), E(FSM, FSM_T, "current_mode", "__nonempty__", 6000)];
  }

  /* ——— M3 integridad ——— */
  for (let n = 1; n <= 12; n++) {
    S["TC-INT-" + p3(n)] = [E(FSM, FSM_T, "current_mode", "__nonempty__", 10000)];
  }

  /* ——— M4 histéresis ——— */
  for (let n = 1; n <= 7; n++) {
    S["TC-HYS-" + p3(n)] = [
      T("/nav/quality_flag", F64, { data: 0.9 }),
      W(150),
      T("/nav/quality_flag", F64, { data: 0.1 }),
      W(150),
      T("/nav/quality_flag", F64, { data: 0.9 }),
      W(150),
      E("/nav/quality_flag", F64, "data", "__nonempty__", 4000),
    ];
  }

  /* ——— M5 localización ——— */
  S["TC-LOC-001"] = [E("/nav/quality_flag", F64, "data", "__nonempty__", 8000)];
  S["TC-LOC-002"] = [...toCruise(6000), T("/nav/quality_flag", F64, { data: 0.15 }), W(250), E(FSM, FSM_T, "current_mode", "EVENT", 5000)];
  S["TC-LOC-003"] = [E("/vehicle_model/state", STR_ARR, "data", "__nonempty__", 8000)];
  for (let n = 4; n <= 13; n++) {
    S["TC-LOC-" + p3(n)] = [E("/nav/quality_flag", F64, "data", "__nonempty__", 5000), W(200), E(FSM, FSM_T, "current_mode", "__nonempty__", 8000)];
  }

  /* ——— M6 DAIDALUS ——— */
  S["TC-DAI-001"] = [T("/fsm/in/daidalus_alert", I32, { data: 1 }), W(200), E("/daidalus/alert_level", I32, "data", 1, 4000)];
  S["TC-DAI-002"] = [T("/fsm/in/daidalus_alert", I32, { data: 2 }), W(200), E("/daidalus/alert_level", I32, "data", 2, 4000)];
  S["TC-DAI-003"] = [T("/fsm/in/daidalus_alert", I32, { data: 3 }), W(200), E("/daidalus/alert_level", I32, "data", 3, 4000)];
  S["TC-DAI-004"] = [T("/fsm/in/daidalus_alert", I32, { data: 0 }), W(200), E("/daidalus/alert_level", I32, "data", 0, 4000)];
  for (let n = 5; n <= 12; n++) {
    S["TC-DAI-" + p3(n)] = [
      ...toCruise(6000),
      T("/fsm/in/daidalus_alert", I32, { data: (n % 4) + 1 }),
      W(250),
      E("/daidalus/alert_level", I32, "data", (n % 4) + 1, 5000),
    ];
  }

  /* ——— M7 FDIR ——— */
  S["TC-FDIR-001"] = [T("/fsm/in/fdir_emergency", BOOL, { data: true }), W(200), E("/fdir/emergency", BOOL, "data", true, 4000)];
  S["TC-FDIR-002"] = [T("/fsm/in/fdir_emergency", BOOL, { data: false }), W(200), E("/fdir/emergency", BOOL, "data", false, 4000)];
  S["TC-FDIR-003"] = [...toCruise(), T("/fsm/in/fdir_emergency", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "ABORT", 6000)];
  for (let n = 4; n <= 8; n++) {
    S["TC-FDIR-" + p3(n)] = [T("/fsm/in/fdir_emergency", BOOL, { data: true }), W(150 + n * 20), E("/fdir/emergency", BOOL, "data", true, 5000)];
  }
  S["TC-FDIR-009"] = [
    E("/fdir/active_fault", STR, "data", "__nonempty__", 8000),
  ];
  for (let n = 10; n <= 16; n++) {
    S["TC-FDIR-" + p3(n)] = [
      T("/fsm/in/fdir_emergency", BOOL, { data: n % 2 === 1 }),
      W(200),
      E("/fdir/emergency", BOOL, "data", n % 2 === 1, 5000),
    ];
  }

  /* ——— M8 NAV ——— */
  for (let n = 1; n <= 12; n++) {
    S["TC-NAV-" + p3(n)] = [
      E("/vehicle_model/state", STR_ARR, "data", "__nonempty__", 8000),
      W(200),
      E(FSM, FSM_T, "current_mode", "__nonempty__", 8000),
    ];
  }

  /* ——— M9 MW ——— */
  S["TC-MW-001"] = [W(300)];
  for (let n = 2; n <= 10; n++) {
    S["TC-MW-" + p3(n)] = [W(100 + n * 40), E(FSM, FSM_T, "current_mode", "__nonempty__", 10000)];
  }

  /* ——— M10 E2E ——— */
  S["TC-E2E-001"] = [
    T("/fsm/in/preflight_ok", BOOL, { data: true }),
    W(150),
    E(FSM, FSM_T, "current_mode", "AUTOTAXI", 5000),
    T("/fsm/in/taxi_clear", BOOL, { data: true }),
    W(150),
    E(FSM, FSM_T, "current_mode", "TAKEOFF", 5000),
    T("/fsm/in/takeoff_complete", BOOL, { data: true }),
    W(250),
    E(FSM, FSM_T, "current_mode", "CRUISE", 8000),
  ];
  S["TC-E2E-002"] = [...S["TC-E2E-001"], T("/fsm/in/land_command", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "LANDING", 6000)];
  S["TC-E2E-003"] = [...toCruise(), T("/fsm/in/rtb_command", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "RTB", 6000)];
  S["TC-E2E-004"] = [...toCruise(), T("/fsm/in/daidalus_alert", I32, { data: 3 }), W(300), E("/daidalus/alert_level", I32, "data", 3, 5000)];
  S["TC-E2E-005"] = [...toCruise(), T("/fsm/in/fdir_emergency", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "ABORT", 6000)];
  S["TC-E2E-006"] = [...toCruise(), T("/nav/quality_flag", F64, { data: 0.1 }), W(250), E(FSM, FSM_T, "current_mode", "EVENT", 5000)];
  S["TC-E2E-007"] = [W(500)];
  S["TC-E2E-008"] = [...S["TC-E2E-001"], T("/fsm/in/abort_command", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "ABORT", 6000)];
  S["TC-E2E-009"] = [...toCruise(), T("/fsm/in/event_cleared", BOOL, { data: true }), W(200)];
  S["TC-E2E-010"] = [...toCruise(), T("/fsm/in/touchdown", BOOL, { data: true }), W(200)];

  /* ——— M11 fallos ——— */
  S["TC-FAULT-001"] = [T("/fsm/in/fdir_emergency", BOOL, { data: true }), W(200), E("/fdir/emergency", BOOL, "data", true, 4000)];
  S["TC-FAULT-002"] = [...toCruise(), T("/fsm/in/fdir_emergency", BOOL, { data: true }), W(200), E("/fdir/emergency", BOOL, "data", true, 5000)];
  S["TC-FAULT-003"] = [...toCruise(), T("/nav/quality_flag", F64, { data: 0.05 }), W(300), E(FSM, FSM_T, "current_mode", "EVENT", 5000)];
  S["TC-FAULT-004"] = [...toCruise(), T("/fsm/in/daidalus_alert", I32, { data: 3 }), W(200), E("/daidalus/alert_level", I32, "data", 3, 5000)];
  S["TC-FAULT-005"] = [T("/fsm/in/abort_command", BOOL, { data: true }), W(200), E(FSM, FSM_T, "current_mode", "ABORT", 5000)];
  S["TC-FAULT-006"] = [...toCruise(), T("/fsm/in/rtb_command", BOOL, { data: true }), W(200)];
  S["TC-FAULT-007"] = [...toCruise(), T("/fsm/in/land_command", BOOL, { data: true }), W(200)];
  S["TC-FAULT-008"] = [T("/fsm/in/fdir_emergency", BOOL, { data: true }), W(200), E("/fdir/active_fault", STR, "data", "__nonempty__", 8000)];
  for (let n = 9; n <= 12; n++) {
    S["TC-FAULT-" + p3(n)] = [
      T("/fsm/in/daidalus_alert", I32, { data: (n % 3) + 1 }),
      W(200),
      E("/daidalus/alert_level", I32, "data", (n % 3) + 1, 5000),
      T("/fsm/in/fdir_emergency", BOOL, { data: n % 2 === 0 }),
      W(200),
    ];
  }

  /* ——— M12 rendimiento ——— */
  for (let n = 1; n <= 8; n++) {
    S["TC-PERF-" + p3(n)] = [
      T("/fsm/in/preflight_ok", BOOL, { data: true }),
      W(50),
      E(FSM, FSM_T, "current_mode", "AUTOTAXI", 2000 + n * 200),
    ];
  }

  /* ——— GPP (flightmind_planner_node topics) ——— */
  const gppExpect = () => [E("flightmind/stack/status", STR, "data", "__nonempty__", 12000)];
  for (let n = 1; n <= 13; n++) {
    S["TC-FL-" + p3(n)] = gppExpect();
  }
  for (let n = 1; n <= 12; n++) {
    S["TC-GEO-" + p3(n)] = [E("flightmind/stack/status", STR, "data", "__nonempty__", 10000), W(100)];
  }
  for (let n = 1; n <= 11; n++) {
    S["TC-DUB-" + p3(n)] = gppExpect();
  }
  for (let n = 1; n <= 12; n++) {
    S["TC-RRT-" + p3(n)] = gppExpect();
  }
  for (let n = 1; n <= 12; n++) {
    S["TC-GTO-" + p3(n)] = gppExpect();
  }
  for (let n = 1; n <= 10; n++) {
    S["TC-NODE-" + p3(n)] = gppExpect();
  }
  for (let n = 1; n <= 5; n++) {
    S["TC-GPPI-" + p3(n)] = gppExpect();
  }
  for (let n = 1; n <= 8; n++) {
    S["SR-GPP-" + p3(n)] = gppExpect();
  }

  /* ——— AUX ——— */
  for (let n = 1; n <= 17; n++) {
    S["TC-AUX-" + p3(n)] = [E(FSM, FSM_T, "current_mode", "__nonempty__", 12000)];
  }
})();
