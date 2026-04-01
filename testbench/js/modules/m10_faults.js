/** M10 — E2E fault injection */
(function () {
  const T = (topic, type, msg) => ({ action: "publish", topic, type, msg });
  const E = (topic, type, field, value, timeout_ms) => ({
    action: "expect",
    topic,
    type,
    field: field || "data",
    value,
    timeout_ms: timeout_ms || 4000,
  });
  const W = (ms) => ({ action: "wait_ms", ms });

  window.M10FLT = {
    id: "M10",
    title: "M10 — E2E Faults",
    tcs: [
      {
        id: "TC-FAULT-001",
        name: "Inyección emergencia FDIR (dashboard)",
        module: "M10",
        steps: [T("/fsm/in/fdir_emergency", "std_msgs/Bool", { data: true }), W(200), E("/fdir/emergency", "std_msgs/Bool", "data", true, 4000)],
      },
      {
        id: "TC-FAULT-008",
        name: "Watchdog / estado emergencia",
        module: "M10",
        steps: [T("/fsm/in/fdir_emergency", "std_msgs/Bool", { data: true }), W(200), E("/fdir/emergency", "std_msgs/Bool", "data", true, 5000)],
      },
    ],
  };
})();
