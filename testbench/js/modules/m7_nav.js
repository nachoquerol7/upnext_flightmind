/** M7 — Nav2 (map + waypoints demo) */
(function () {
  window.M7NAV = {
    id: "M7",
    title: "M7 — Nav2",
    tcs: [],
    mount(root) {
      root.innerHTML = "";
      const c = document.createElement("canvas");
      c.className = "map-canvas";
      c.width = 520;
      c.height = 360;
      root.appendChild(c);
      this._map = new Map2D(c);
      this._map.waypoints = [
        { x: 60, y: 320 },
        { x: 180, y: 260 },
        { x: 320, y: 200 },
        { x: 450, y: 120 },
      ];
      this._map.setActiveRoute([
        { x: 60, y: 320 },
        { x: 180, y: 260 },
        { x: 320, y: 200 },
        { x: 450, y: 120 },
      ]);
      const hint = document.createElement("div");
      hint.className = "placeholder-box";
      hint.style.marginTop = "10px";
      hint.innerHTML =
        "<b>M7 Nav2</b> — Waypoints de referencia. Si existe <code>/gpp/global_path</code> en tu stack, se puede cablear en una iteración posterior.";
      root.appendChild(hint);
    },
    update(st) {
      const arr = st.vehicleState;
      if (arr && arr.length >= 3) {
        const n = Number(arr[0]);
        const e = Number(arr[1]);
        this._map.setVehicle(n, e, st.quality != null ? st.quality : 1);
      }
      this._map.render();
    },
  };
})();
