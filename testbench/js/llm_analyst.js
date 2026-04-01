/**
 * Analista LLM vía proxy local (testbench/llm_proxy.js).
 * La API key de Anthropic no sale del proceso Node del proxy.
 */
(function () {
  "use strict";

  const PROXY_ANALYZE_URL = "http://localhost:3001/analyze";

  /** Comprueba si el proxy responde (CORS preflight). */
  async function checkProxy() {
    try {
      const r = await fetch(PROXY_ANALYZE_URL, { method: "OPTIONS" });
      return r.ok || r.status === 204;
    } catch {
      return false;
    }
  }

  class LLMAnalyst {
    constructor() {
      this.enabled = false;
      /** @type {Record<string, unknown>} */
      this.context = {};
      /** @type {HTMLElement | null} */
      this._outputEl = null;
      /** @type {HTMLElement | null} */
      this._historyEl = null;
      /** @type {HTMLElement | null} */
      this._streamContainer = null;
      /** @type {{ text: string, at: string }[]} */
      this._history = [];
      this._streaming = false;
      /** @type {Promise<void>} */
      this._analyzeChain = Promise.resolve();
      try {
        localStorage.removeItem("anthropic_api_key");
      } catch (_) {
        /* ignore */
      }
    }

    /**
     * @param {HTMLElement | null} outputEl contenedor del texto en curso (streaming)
     * @param {HTMLElement | null} historyEl lista últimos análisis
     */
    bindUi(outputEl, historyEl) {
      this._outputEl = outputEl;
      this._historyEl = historyEl;
      this.refreshHistoryPanel();
    }

    setEnabled(on) {
      this.enabled = Boolean(on);
    }

    onStreamStart() {
      this._streaming = true;
      if (!this._outputEl) return;
      this._outputEl.innerHTML = "";
      this._streamContainer = document.createElement("p");
      this._streamContainer.className = "llm-stream-line";
      this._outputEl.appendChild(this._streamContainer);
      const cursor = document.createElement("span");
      cursor.className = "llm-cursor";
      cursor.textContent = "▍";
      this._streamContainer.appendChild(cursor);
    }

    /**
     * @param {string} chunk
     */
    onToken(chunk) {
      if (!this._streamContainer) return;
      const cursor = this._streamContainer.querySelector(".llm-cursor");
      const textNode = document.createTextNode(chunk);
      if (cursor) this._streamContainer.insertBefore(textNode, cursor);
      else this._streamContainer.appendChild(textNode);
    }

    onStreamEnd() {
      this._streaming = false;
      const cursor = this._streamContainer?.querySelector(".llm-cursor");
      if (cursor) cursor.remove();
      const text = this._streamContainer?.textContent?.trim() || "";
      if (text) {
        this._history.unshift({ text, at: new Date().toISOString() });
        this._history = this._history.slice(0, 3);
        this._renderHistory();
      }
      this._streamContainer = null;
    }

    refreshHistoryPanel() {
      this._renderHistory();
    }

    _renderHistory() {
      if (!this._historyEl) return;
      if (!this._history.length) {
        this._historyEl.innerHTML = '<p class="hint">Sin análisis recientes.</p>';
        return;
      }
      this._historyEl.innerHTML = this._history
        .map(
          (h, i) =>
            `<div class="llm-history-item"><span class="llm-h-idx">#${i + 1}</span><p>${escapeHtml(h.text.slice(0, 400))}${h.text.length > 400 ? "…" : ""}</p></div>`,
        )
        .join("");
    }

    /**
     * Encola análisis para evitar solapamiento de streams en la UI.
     * @param {string} event user prompt
     * @returns {Promise<void>}
     */
    analyze(event) {
      this._analyzeChain = this._analyzeChain
        .then(() => this._doAnalyze(event))
        .catch(() => {});
      return this._analyzeChain;
    }

    async _doAnalyze(event) {
      if (!this.enabled) return;
      const proxyUp = await checkProxy();
      if (!proxyUp) {
        this.onStreamStart();
        this.onToken("[Proxy offline] Arranca testbench con ANTHROPIC_API_KEY o ejecuta node testbench/llm_proxy.js");
        this.onStreamEnd();
        return;
      }

      try {
        this.onStreamStart();
        const response = await fetch(PROXY_ANALYZE_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: event }),
        });

        if (!response.ok) {
          const errText = await response.text();
          this.onToken(`[Error proxy ${response.status}] ${errText.slice(0, 200)}`);
          return;
        }

        const reader = response.body && response.body.getReader();
        if (!reader) {
          this.onToken("[Sin cuerpo de respuesta]");
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n");
          buffer = parts.pop() || "";
          for (const line of parts) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data:")) continue;
            const payload = trimmed.slice(5).trim();
            if (payload === "[DONE]") continue;
            try {
              const data = JSON.parse(payload);
              if (data.type === "content_block_delta" && data.delta) {
                const d = data.delta;
                if (typeof d.text === "string") this.onToken(d.text);
                else if (d.type === "text_delta" && typeof d.text === "string") this.onToken(d.text);
              }
            } catch (_) {
              /* ignore partial JSON */
            }
          }
        }
      } catch (e) {
        if (!this._streamContainer) this.onStreamStart();
        this.onToken(String(e && e.message ? e.message : e));
      } finally {
        this.onStreamEnd();
      }
    }
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  window.LLMAnalyst = LLMAnalyst;
  window.checkLlmProxy = checkProxy;
})();
