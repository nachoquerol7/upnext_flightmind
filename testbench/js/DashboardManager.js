/**
 * Orquesta el layout modular en #main-display (rejillas 1 / 2 / 4).
 */
class DashboardManager {
  /**
   * @param {RosBridge | null} bridge
   */
  constructor(bridge) {
    this.bridge = bridge;
    this.rootId = "main-display";
    /** @type {BasePanel[]} */
    this._panels = [];
  }

  setBridge(bridge) {
    this.bridge = bridge;
  }

  /**
   * @param {string[]} panelIds nombres de clase globales (ej. "RadarPanel")
   * @param {import('./tc_runner').TestCase | null} tc
   */
  loadLayout(panelIds, tc) {
    this.destroy();
    const el = document.getElementById(this.rootId);
    if (!el) return;

    const ids = (panelIds || []).filter(Boolean);
    if (ids.length === 0) ids.push("FsmGraphPanel");

    el.className = "dashboard-root";
    if (ids.length <= 1) el.classList.add("grid-1");
    else if (ids.length === 2) el.classList.add("grid-2");
    else el.classList.add("grid-4");

    ids.forEach((name) => {
      const slot = document.createElement("div");
      slot.className = "dashboard-panel-slot";
      slot.dataset.panel = name;
      el.appendChild(slot);

      const Ctor = window[name];
      if (typeof Ctor !== "function") {
        slot.innerHTML = `<div class="panel-unknown">Panel desconocido: <code>${this._esc(name)}</code></div>`;
        return;
      }
      try {
        const panel = new Ctor(slot, this.bridge);
        panel.mount();
        panel.flushRosSubscriptions();
        panel.onTCStart(tc);
        this._panels.push(panel);
      } catch (e) {
        console.error("DashboardManager mount", name, e);
        slot.innerHTML = `<div class="panel-error">${this._esc(String(e))}</div>`;
      }
    });
  }

  _esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  destroy() {
    this._panels.forEach((p) => {
      try {
        p.unmount();
      } catch (e) {
        console.error(e);
      }
    });
    this._panels = [];
    const el = document.getElementById(this.rootId);
    if (el) {
      el.innerHTML = "";
      el.className = "";
    }
  }

  /** Propaga mensaje ROS a todos los paneles montados. */
  broadcast(topic, msg) {
    const env = { topic, msg };
    this._panels.forEach((p) => {
      try {
        if (typeof p.onMessage === "function") p.onMessage(env);
      } catch (e) {
        console.error(e);
      }
    });
  }

  syncFromState(state) {
    this._panels.forEach((p) => {
      try {
        if (typeof p.syncFromState === "function") p.syncFromState(state);
      } catch (e) {
        console.error(e);
      }
    });
  }

  forEachPanel(fn) {
    this._panels.forEach(fn);
  }

  get firstPanel() {
    return this._panels[0] || null;
  }

  /** Tras conectar rosbridge: suscripciones diferidas en cada panel. */
  flushAllPanelRosSubscriptions() {
    this._panels.forEach((p) => {
      try {
        if (typeof p.flushRosSubscriptions === "function") p.flushRosSubscriptions();
      } catch (e) {
        console.error(e);
      }
    });
  }
}

window.DashboardManager = DashboardManager;
