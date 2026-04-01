/**
 * Test case runner: ordered publish / expect steps
 */
class TCRunner {
  /**
   * @param {RosBridge} bridge
   * @param {(line: string) => void} logFn
   */
  constructor(bridge, logFn) {
    this.bridge = bridge;
    this.log = logFn || console.log;
    /** @type {Array<() => void>} */
    this._subs = [];
  }

  _ts() {
    return new Date().toISOString().split("T")[1].replace("Z", "");
  }

  clearSubscriptions() {
    this._subs.forEach((u) => {
      try {
        u();
      } catch (_) {}
    });
    this._subs = [];
  }

  /**
   * @param {object} msg
   * @param {string} field - dot path e.g. current_mode or data
   */
  _getField(msg, field) {
    if (!field) return msg;
    const parts = field.split(".");
    let o = msg;
    for (const p of parts) {
      if (o == null) return undefined;
      o = o[p];
    }
    return o;
  }

  /**
   * @param {import('./tc_runner').TCStep} step
   */
  async _runStep(step, tcId) {
    if (step.action === "publish") {
      if (!this.bridge.connected) throw new Error("Not connected");
      this.bridge.publish(step.topic, step.type, step.msg);
      const line = `[${this._ts()}] ${tcId} PUBLISH ${step.topic} ${JSON.stringify(step.msg)}`;
      this.log(line);
      return { ok: true, line };
    }
    if (step.action === "expect") {
      const timeoutMs = step.timeout_ms ?? 5000;
      const topic = step.topic;
      const type = step.type;
      const field = step.field || "data";
      const want = step.value;
      const wantNum = typeof want === "number" ? want : null;

      return await new Promise((resolve) => {
        let done = false;
        const to = setTimeout(() => {
          if (done) return;
          done = true;
          try {
            unsub();
          } catch (_) {}
          resolve({
            ok: false,
            line: `[${this._ts()}] ${tcId} FAIL expect ${topic} ${field} === ${JSON.stringify(want)} (timeout ${timeoutMs}ms)`,
            got: null,
            evidence: `FAIL: Timeout esperando ${topic} ${field} === ${JSON.stringify(want)} tras ${timeoutMs}ms`,
          });
        }, timeoutMs);

        const t0 = Date.now();
        const unsub = this.bridge.subscribe(topic, type, (msg) => {
          if (done) return;
          let got = this._getField(msg, field);
          if (got && typeof got === "object" && "data" in got && field.indexOf(".") === -1) {
            got = got.data;
          }
          let match = false;
          if (want === "__nonempty__") {
            if (got != null && typeof got.length === "number" && typeof got !== "string") {
              match = got.length > 0;
            } else {
              match = got != null && String(got).trim().length > 0;
            }
          } else if (wantNum !== null && typeof want === "number") {
            match = Number(got) === wantNum;
          } else if (typeof want === "boolean") {
            match = Boolean(got) === want;
          } else {
            match = got === want || String(got) === String(want);
          }
          if (match) {
            done = true;
            clearTimeout(to);
            try {
              unsub();
            } catch (_) {}
            const elapsed = Date.now() - t0;
            const line = `[${this._ts()}] ${tcId} OK expect ${topic} ${field} === ${JSON.stringify(want)}`;
            this.log(line);
            const evidence = `PASS: ${field} = ${JSON.stringify(got)} recibido en ${elapsed}ms (límite: ${timeoutMs}ms)`;
            resolve({ ok: true, line, got, elapsedMs: elapsed, evidence });
          }
        });
        this._subs.push(unsub);
      });
    }
    if (step.action === "wait_ms" || step.action === "wait") {
      const ms = step.ms ?? 200;
      await new Promise((r) => setTimeout(r, ms));
      return { ok: true, line: `[${this._ts()}] ${tcId} wait ${ms}ms` };
    }
    throw new Error("Unknown step action: " + step.action);
  }

  /**
   * @param {import('./tc_runner').TestCase} tc
   * @returns {Promise<{pass: boolean, detail: string}>}
   */
  async run(tc) {
    this.clearSubscriptions();
    const lines = [];
    /** @type {string} */
    let lastEvidence = "";
    const tStart = Date.now();
    const stepsTotal = (tc.steps && tc.steps.length) || 0;
    let stepsOk = 0;
    try {
      for (const step of tc.steps) {
        const r = await this._runStep(step, tc.id);
        if (r.line) lines.push(r.line);
        if (r.ok !== false) stepsOk += 1;
        if (step.action === "expect") {
          if (r.evidence) lastEvidence = r.evidence;
          if (!r.ok) {
            return {
              pass: false,
              detail: r.got != null ? `got ${JSON.stringify(r.got)}` : r.line || "expect failed",
              evidence: r.evidence || r.line || "FAIL",
              durationMs: Date.now() - tStart,
              stepsOk,
              stepsTotal,
            };
          }
        }
      }
      return {
        pass: true,
        detail: lines.join("\n"),
        evidence: lastEvidence || lines[lines.length - 1] || "PASS",
        durationMs: Date.now() - tStart,
        stepsOk,
        stepsTotal,
      };
    } catch (e) {
      return {
        pass: false,
        detail: String(e && e.message ? e.message : e),
        evidence: String(e && e.message ? e.message : e),
        durationMs: Date.now() - tStart,
        stepsOk,
        stepsTotal,
      };
    } finally {
      this.clearSubscriptions();
    }
  }
}

/** @typedef {{ action: 'publish', topic: string, type: string, msg: object }} TCPublish */
/** @typedef {{ action: 'expect', topic: string, type: string, field?: string, value: *, timeout_ms?: number }} TCExpect */
/** @typedef {{ action: 'wait_ms' | 'wait', ms: number }} TCWait */
/** @typedef {TCPublish | TCExpect | TCWait} TCStep */
/** @typedef {{ id: string, name: string, module: string, timeout_ms?: number, max_duration_sec?: number, steps: TCStep[] }} TestCase */

window.TCRunner = TCRunner;
