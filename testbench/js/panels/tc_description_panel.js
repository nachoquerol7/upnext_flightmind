/**
 * Panel central: metadatos del TC seleccionado (plan V&V).
 */
(function () {
  "use strict";

  function esc(s) {
    if (s == null) return "";
    const d = document.createElement("div");
    d.textContent = String(s);
    return d.innerHTML;
  }

  function formatParams(params) {
    if (!params || !params.length) return "—";
    return params.map((p) => esc(p)).join(" · ");
  }

  function formatRefs(refs) {
    if (!refs || !refs.length) return "—";
    return refs.map((r) => esc(r)).join(" · ");
  }

  class TCDescriptionPanel {
    /**
     * @param {HTMLElement | null} root
     */
    constructor(root) {
      this.root = root;
    }

    mount() {
      if (!this.root) return;
      this.root.innerHTML =
        '<div class="tc-desc-panel tc-desc-empty"><p class="tc-desc-placeholder">Selecciona un TC en el sidebar.</p></div>';
    }

    /**
     * @param {{ id: string, name?: string, title?: string, definition?: object } | null} tc
     */
    show(tc) {
      if (!this.root) return;
      const def = (tc && tc.definition) || (tc && window.getTcDefinition && window.getTcDefinition(tc.id)) || null;
      if (!tc || !def) {
        this.mount();
        return;
      }

      const priClass = (def.priority || "P1").toLowerCase();
      const title = def.title || tc.name || tc.title || tc.id;
      const xfailNote = def.xfail
        ? `<div class="tc-xfail-banner">Marcado como XFAIL / gap: ${esc(def.xfail)} — <a href="docs/vnv/XFAIL_INDEX.md" target="_blank" rel="noopener">XFAIL_INDEX.md</a></div>`
        : "";

      this.root.innerHTML = `
<div class="tc-desc-panel">
  ${xfailNote}
  <div class="tc-header">
    <span class="tc-id">${esc(def.id)}</span>
    <span class="tc-title">${esc(title)}</span>
    <span class="priority ${priClass}">${esc(def.priority || "P1")}</span>
    <span class="module">${esc(def.moduleTitle || def.module || "")}</span>
  </div>
  <div class="tc-body">
    <div class="field">
      <label>Qué se prueba</label>
      <p>${esc(def.what)}</p>
    </div>
    <div class="field">
      <label>Parámetros clave</label>
      <code class="tc-params">${formatParams(def.params)}</code>
    </div>
    <div class="field">
      <label>Oráculo</label>
      <p>${esc(def.oracle)}</p>
    </div>
    <div class="field">
      <label>Criterios visuales</label>
      <p><strong>PASS:</strong> ${esc(def.pass_visual)}<br/><strong>FAIL:</strong> ${esc(def.fail_visual)}</p>
    </div>
    <div class="field">
      <label>Referencia</label>
      <p>${formatRefs(def.references)}</p>
    </div>
  </div>
</div>`;
    }
  }

  window.TCDescriptionPanel = TCDescriptionPanel;
})();
