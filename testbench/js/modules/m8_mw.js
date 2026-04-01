/** M8 — Middleware ROS / latencia */
(function () {
  const W = (ms) => ({ action: "wait_ms", ms });

  window.M8MW = {
    id: "M8",
    title: "M8 — Middleware ROS",
    tcs: [
      {
        id: "TC-MW-001",
        name: "Latencia / intervalos (proxy P99)",
        module: "M8",
        steps: [W(300)],
      },
    ],
  };
})();
