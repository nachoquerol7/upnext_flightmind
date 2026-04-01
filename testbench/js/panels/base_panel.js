/**
 * Base class for per-TC visual panels.
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
    /** @type {HTMLElement | null} */
    this._overlayEl = null;
    /** Congela actualizaciones en vivo tras veredicto hasta Limpiar */
    this._frozen = false;
  }

  mount() {}

  /**
   * @param {string} topic
   * @param {object} msg
   */
  onMessage(topic, msg) {}

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
