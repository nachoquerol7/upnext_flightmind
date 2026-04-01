/** M4 — Localization */
(function () {
  const E = (topic, type, field, value, timeout_ms) => ({
    action: "expect",
    topic,
    type,
    field,
    value,
    timeout_ms: timeout_ms || 8000,
  });

  window.M4LOC = {
    id: "M4",
    title: "M4 — Localización",
    tcs: [
      {
        id: "TC-LOC-001",
        name: "Señal quality_flag presente",
        module: "M4",
        steps: [E("/nav/quality_flag", "std_msgs/Float64", "data", "__nonempty__", 8000)],
      },
      {
        id: "TC-LOC-003",
        name: "Estado vehículo publicado",
        module: "M4",
        steps: [E("/vehicle_model/state", "std_msgs/Float64MultiArray", "data", "__nonempty__", 8000)],
      },
    ],
  };
})();
