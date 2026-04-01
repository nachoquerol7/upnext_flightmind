/** M1 — FSM transitions */
(function () {
  const T = (topic, type, msg) => ({ action: "publish", topic, type, msg });
  const E = (topic, type, field, value, timeout_ms) => ({
    action: "expect",
    topic,
    type,
    field,
    value,
    timeout_ms: timeout_ms || 4000,
  });
  const W = (ms) => ({ action: "wait_ms", ms });

  const MODE = "/fsm/current_mode";
  const STR = "std_msgs/String";

  window.M1FSM = {
    id: "M1",
    title: "M1 — FSM Transitions",
    tcs: [
      {
        id: "TC-FSM-001",
        name: "PREFLIGHT → AUTOTAXI",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(350),
          E(MODE, STR, "data", "AUTOTAXI", 8000),
        ],
      },
      {
        id: "TC-FSM-002",
        name: "AUTOTAXI → TAKEOFF",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(150),
          E(MODE, STR, "data", "AUTOTAXI", 5000),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(150),
          E(MODE, STR, "data", "TAKEOFF", 5000),
        ],
      },
      {
        id: "TC-FSM-003",
        name: "TAKEOFF → CRUISE",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/takeoff_complete", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "CRUISE", 6000),
        ],
      },
      {
        id: "TC-FSM-004",
        name: "CRUISE → EVENT (quality)",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/takeoff_complete", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "CRUISE", 6000),
          T("/fsm/in/quality_flag", "std_msgs/Float64", { data: 0.1 }),
          W(250),
          E(MODE, STR, "data", "EVENT", 5000),
        ],
      },
      {
        id: "TC-FSM-005",
        name: "CRUISE → RTB",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/takeoff_complete", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "CRUISE", 6000),
          T("/fsm/in/rtb_command", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "RTB", 5000),
        ],
      },
      {
        id: "TC-FSM-006",
        name: "CRUISE → LANDING",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/takeoff_complete", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "CRUISE", 6000),
          T("/fsm/in/land_command", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "LANDING", 5000),
        ],
      },
      {
        id: "TC-FSM-007",
        name: "EVENT → CRUISE (event_cleared)",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/takeoff_complete", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "CRUISE", 6000),
          T("/fsm/in/quality_flag", "std_msgs/Float64", { data: 0.1 }),
          W(250),
          E(MODE, STR, "data", "EVENT", 5000),
          T("/fsm/in/quality_flag", "std_msgs/Float64", { data: 1.0 }),
          W(150),
          T("/fsm/in/event_cleared", "std_msgs/Bool", { data: true }),
          W(250),
          E(MODE, STR, "data", "CRUISE", 6000),
        ],
      },
      {
        id: "TC-FSM-008",
        name: "CRUISE → ABORT (fdir_emergency)",
        module: "M1",
        steps: [
          T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/taxi_clear", "std_msgs/Bool", { data: true }),
          W(120),
          T("/fsm/in/takeoff_complete", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "CRUISE", 6000),
          T("/fsm/in/fdir_emergency", "std_msgs/Bool", { data: true }),
          W(200),
          E(MODE, STR, "data", "ABORT", 5000),
        ],
      },
    ],
  };
})();
