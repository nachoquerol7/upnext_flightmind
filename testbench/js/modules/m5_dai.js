/** M5 — DAIDALUS */
(function () {
  const T = (topic, type, msg) => ({ action: "publish", topic, type, msg });
  const E = (topic, type, field, value, timeout_ms) => ({
    action: "expect",
    topic,
    type,
    field: field || "data",
    value,
    timeout_ms: timeout_ms || 3000,
  });
  const W = (ms) => ({ action: "wait_ms", ms });

  window.M5DAI = {
    id: "M5",
    title: "M5 — DAIDALUS",
    tcs: [
      {
        id: "TC-DAI-001",
        name: "Alert level FAR (1)",
        module: "M5",
        steps: [T("/fsm/in/daidalus_alert", "std_msgs/Int32", { data: 1 }), W(200), E("/daidalus/alert_level", "std_msgs/Int32", "data", 1, 4000)],
      },
      {
        id: "TC-DAI-002",
        name: "Alert level MID (2)",
        module: "M5",
        steps: [T("/fsm/in/daidalus_alert", "std_msgs/Int32", { data: 2 }), W(200), E("/daidalus/alert_level", "std_msgs/Int32", "data", 2, 4000)],
      },
      {
        id: "TC-DAI-003",
        name: "Alert level NEAR (3) + FSM EVENT",
        module: "M5",
        steps: [
          T("/fsm/in/daidalus_alert", "std_msgs/Int32", { data: 3 }),
          W(200),
          E("/daidalus/alert_level", "std_msgs/Int32", "data", 3, 4000),
        ],
      },
      {
        id: "TC-DAI-004",
        name: "Clear alert (0)",
        module: "M5",
        steps: [T("/fsm/in/daidalus_alert", "std_msgs/Int32", { data: 0 }), W(200), E("/daidalus/alert_level", "std_msgs/Int32", "data", 0, 4000)],
      },
    ],
  };
})();
