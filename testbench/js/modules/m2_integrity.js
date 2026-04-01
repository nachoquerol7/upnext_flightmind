/** M2 — Timeouts / integridad (placeholder steps) */
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

  window.M2INT = {
    id: "M2",
    title: "M2 — Integrity / Timeouts",
    tcs: [
      {
        id: "TC-TO-001",
        name: "Timeout visual en estado (barras)",
        module: "M2",
        max_duration_sec: 5,
        steps: [T("/fsm/in/preflight_ok", "std_msgs/Bool", { data: true }), W(150), E(MODE, STR, "data", "AUTOTAXI", 5000)],
      },
    ],
  };
})();
