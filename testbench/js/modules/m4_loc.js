/** M4 — Localization */
(function () {
  window.M4LOC = {
    id: "M4",
    title: "M4 — Localización",
    tcs: [],
    mount(root) {
      root.innerHTML = "";
      const row = document.createElement("div");
      row.className = "display-row";
      const c1 = document.createElement("canvas");
      c1.className = "map-canvas";
      c1.width = 420;
      c1.height = 280;
      const c2 = document.createElement("canvas");
      c2.className = "alt-canvas";
      c2.width = 420;
      c2.height = 140;
      row.appendChild(c1);
      row.appendChild(c2);
      root.appendChild(row);
      this._map = new Map2D(c1);
      this._alt = new AltitudeProfile(c2);
      const hint = document.createElement("div");
      hint.style.marginTop = "8px";
      hint.style.color = "#8aa4bc";
      hint.style.fontSize = "11px";
      hint.textContent =
        "Mapa: posición desde /vehicle_model/state [0,1]→N/E; trail 120s ponderado por quality. Altitud: -state[2] NED.";
      root.appendChild(hint);
    },
    update(st) {
      const arr = st.vehicleState;
      if (arr && arr.length >= 3) {
        const n = Number(arr[0]);
        const e = Number(arr[1]);
        this._map.setVehicle(n, e, st.quality != null ? st.quality : 1);
        this._alt.pushFromVehicleArray(arr);
      }
      this._map.render();
      this._alt.render();
    },
  };
})();
