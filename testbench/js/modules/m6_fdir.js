/** M6 — FDIR */
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

  window.M6FDIR = {
    id: "M6",
    title: "M6 — FDIR",
    tcs: [
      {
        id: "TC-FDIR-001",
        name: "fdir_emergency true",
        module: "M6",
        steps: [T("/fsm/in/fdir_emergency", "std_msgs/Bool", { data: true }), W(200), E("/fdir/emergency", "std_msgs/Bool", "data", true, 4000)],
      },
      {
        id: "TC-FDIR-002",
        name: "fdir_emergency false (reset)",
        module: "M6",
        steps: [T("/fsm/in/fdir_emergency", "std_msgs/Bool", { data: false }), W(200), E("/fdir/emergency", "std_msgs/Bool", "data", false, 4000)],
      },
      {
        id: "TC-FDIR-009",
        name: "active_fault string publicado",
        module: "M6",
        steps: [
          {
            action: "expect",
            topic: "/fdir/active_fault",
            type: "std_msgs/String",
            field: "data",
            value: "__nonempty__",
            timeout_ms: 8000,
          },
        ],
      },
    ],
    mount(root) {
      root.innerHTML = "";
      FdirTree.mount(root);
    },
    update(st) {
      FdirTree.update(st);
    },
  };
})();
