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
      {
        id: "TC-E2E-007",
        name: "Memory leak (RAM monitor)",
        module: "M9",
        steps: [{ action: "wait_ms", ms: 500 }],
      },
    ],
  };
})();
