/**
 * Resultados de la última ejecución del TC activo + export puntual.
 */
(function () {
  "use strict";

  class ResultsPanel {
    /**
     * @param {HTMLElement | null} root
     * @param {(ev: CustomEvent) => void} [onExportTc]
     */
    constructor(root, onExportTc) {
      this.root = root;
      this.onExportTc = onExportTc;
      this._lastPayload = null;
    }

    mount() {
      if (!this.root) return;
      this._renderEmpty();
    }

    _renderEmpty() {
      if (!this.root) return;
      this.root.innerHTML =
        '<div class="results-panel results-panel-empty"><p class="results-placeholder">Ejecuta un TC para ver veredicto y evidencia.</p></div>';
      this._lastPayload = null;
    }

    /**
     * @param {object} payload
     * @param {string} payload.tcId
     * @param {boolean} payload.pass
     * @param {string} [payload.evidence]
     * @param {string} [payload.detail]
     * @param {number} payload.durationMs
     * @param {string} payload.stepsLabel e.g. "2/2 OK"
     * @param {string} payload.timestamp
     * @param {string | null} [payload.xfail]
     */
    show(payload) {
      if (!this.root) return;
      this._lastPayload = payload;
      const isXfailExpected = Boolean(payload.xfail && !payload.pass);
      const verdictClass = isXfailExpected ? "xfail" : payload.pass ? "pass" : "fail";
      const verdictText = isXfailExpected ? "XFAIL" : payload.pass ? "PASS" : "FAIL";
      const xfailBlock =
        payload.xfail && !payload.pass
          ? `<div class="results-xfail-meta">Gap / arquitectura: ${escapeHtml(payload.xfail)} · <a href="docs/vnv/XFAIL_INDEX.md" target="_blank" rel="noopener">XFAIL_INDEX.md</a></div>`
          : payload.xfail && payload.pass
            ? `<div class="results-xfail-meta warn">TC marcado XFAIL pero ejecutó PASS — revisar definición.</div>`
            : "";

      this.root.innerHTML = `
<div class="results-panel ${isXfailExpected ? "results-xfail-panel" : ""}">
  <div class="verdict ${verdictClass}">${verdictText}</div>
  <div class="evidence">${escapeHtml(payload.evidence || payload.detail || "—")}</div>
  ${xfailBlock}
  <div class="timing">
    <span>Duración: ${Math.round(payload.durationMs)}ms</span>
    <span>Steps: ${escapeHtml(payload.stepsLabel)}</span>
    <span>${escapeHtml(payload.timestamp)}</span>
  </div>
  <div class="results-actions">
    <button type="button" class="btn-clear">Limpiar</button>
    <button type="button" class="btn-export-tc">Exportar este TC</button>
  </div>
</div>`;

      this.root.querySelector(".btn-clear")?.addEventListener("click", () => this._renderEmpty());
      this.root.querySelector(".btn-export-tc")?.addEventListener("click", () => {
        if (typeof this.onExportTc === "function") {
          this.onExportTc(
            new CustomEvent("export-tc", {
              detail: this._lastPayload,
            }),
          );
        } else {
          exportSingleTcJson(this._lastPayload);
        }
      });
    }

    clear() {
      this._renderEmpty();
    }
  }

  function escapeHtml(s) {
    if (s == null) return "";
    const d = document.createElement("div");
    d.textContent = String(s);
    return d.innerHTML;
  }

  function exportSingleTcJson(payload) {
    if (!payload) return;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `flightmind_tc_${payload.tcId}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  window.ResultsPanel = ResultsPanel;
  window.exportSingleTcJson = exportSingleTcJson;
})();
