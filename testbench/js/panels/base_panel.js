/**
 * Clase base para paneles por TC: layout, veredicto, suscripciones ROS2.
 * @abstract
 */
class BasePanel {
  /**
   * @param {HTMLElement} container
   * @param {RosBridge | null} ros
   */
  constructor(container, ros) {
    this.container = container;
    this.ros = ros;
    /** @type {Array<() => void>} */
    this._rosUnsubs = [];
    /** @type {Array<{topic: string, type: string, handler: (msg: object) => void}>} */
    this._pendingRosSubs = [];
    /** @type {HTMLElement | null} */
    this._overlayEl = null;
    this._frozen = false;
  }

  /**
   * Asigna contenedor por id (p. ej. slot del DashboardManager).
   * @param {string} containerId
   */
  init(containerId) {
    const el = document.getElementById(containerId);
    if (el) this.container = el;
  }

  mount() {}

  /**
   * Mensaje ROS encapsulado o firma legacy (topic, msg).
   * @param {{ topic: string, msg: object } | string} messageOrTopic
   * @param {object} [msg]
   */
  onMessage(messageOrTopic, msg) {
    let topic;
    let payload;
    if (typeof messageOrTopic === "string") {
      topic = messageOrTopic;
      payload = msg;
    } else if (messageOrTopic && typeof messageOrTopic === "object" && "topic" in messageOrTopic) {
      topic = messageOrTopic.topic;
      payload = messageOrTopic.msg;
    } else {
      return;
    }
    if (this._frozen) return;
    this.handleTopic(topic, payload);
  }

  /**
   * Sobrescribir en subclases para reaccionar a tópicos (tras onMessage).
   * @param {string} topic
   * @param {object} msg
   */
  handleTopic(topic, msg) {}

  /**
   * Suscripción ROS2 con unsubscribe automático en unmount.
   * Si aún no hay conexión, la petición queda en cola (flushRosSubscriptions).
   * @param {string} topic
   * @param {string} type
   * @param {(msg: object) => void} handler
   */
  subscribeRos(topic, type, handler) {
    const wrapped = (m) => {
      try {
        handler(m);
      } catch (e) {
        console.error(topic, e);
      }
    };
    if (!this.ros || !this.ros.connected || !this.ros.ros) {
      this._pendingRosSubs.push({ topic, type, handler: wrapped });
      return;
    }
    try {
      const u = this.ros.subscribe(topic, type, wrapped);
      this._rosUnsubs.push(u);
    } catch (e) {
      console.warn("subscribeRos deferred:", topic, e);
      this._pendingRosSubs.push({ topic, type, handler: wrapped });
    }
  }

  /** Ejecutar suscripciones pendientes tras rosbridge conectado. */
  flushRosSubscriptions() {
    if (!this.ros || !this.ros.connected || !this.ros.ros) return;
    const q = this._pendingRosSubs.splice(0);
    for (const { topic, type, handler } of q) {
      try {
        const u = this.ros.subscribe(topic, type, handler);
        this._rosUnsubs.push(u);
      } catch (e) {
        console.warn("subscribeRos", topic, e);
        this._pendingRosSubs.push({ topic, type, handler });
      }
    }
  }

  clearRosSubscriptions() {
    this._pendingRosSubs = [];
    (this._rosUnsubs || []).forEach((u) => {
      try {
        u();
      } catch (_) {}
    });
    this._rosUnsubs = [];
  }

  /**
   * @param {object} state — agregado app (fsmState, vehicleState, …)
   */
  syncFromState(state) {}

  /**
   * @param {import('../tc_runner').TestCase | null} tc
   */
  onTCStart(tc) {
    this._frozen = false;
    this._clearOverlay();
  }

  /**
   * @param {{ pass: boolean, detail?: string, evidence?: string }} result
   */
  onTCEnd(result) {
    this._frozen = true;
    const text = result.evidence || result.detail || (result.pass ? "PASS" : "FAIL");
    this._showOverlay(result.pass, text);
  }

  clearVerdict() {
    this._frozen = false;
    this._clearOverlay();
  }

  unmount() {
    this.clearRosSubscriptions();
    this._clearOverlay();
    if (this.container) this.container.innerHTML = "";
  }

  _showOverlay(pass, evidenceText) {
    this._clearOverlay();
    const wrap = document.createElement("div");
    wrap.className = "tb-verdict-overlay " + (pass ? "tb-pass" : "tb-fail");
    wrap.innerHTML = `
      <div class="tb-verdict-inner">
        <div class="tb-verdict-badge">${pass ? "PASS" : "FAIL"}</div>
        <div class="tb-verdict-evidence">${this._esc(evidenceText)}</div>
        <button type="button" class="tb-verdict-clear">Limpiar</button>
      </div>
    `;
    const btn = wrap.querySelector(".tb-verdict-clear");
    btn.addEventListener("click", () => {
      this._frozen = false;
      this._clearOverlay();
    });
    this.container.style.position = "relative";
    this.container.appendChild(wrap);
    this._overlayEl = wrap;
  }

  _clearOverlay() {
    if (this._overlayEl && this._overlayEl.parentNode) {
      this._overlayEl.parentNode.removeChild(this._overlayEl);
    }
    this._overlayEl = null;
  }

  _esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }
}

window.BasePanel = BasePanel;
