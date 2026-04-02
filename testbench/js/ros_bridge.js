/**
 * ROS2 bridge via rosbridge WebSocket + roslibjs
 * @see https://github.com/RobotWebTools/roslibjs
 */

const ROSBRIDGE_PORT = 9090;

/**
 * Candidatos WebSocket: primero el mismo host que sirve la UI (LAN u host local),
 * luego 127.0.0.1 y localhost para compatibilidad con file:// y políticas del navegador.
 * @returns {string[]}
 */
function rosbridgeWebSocketCandidates() {
  const out = [];
  const add = (host) => {
    if (!host) return;
    const u = `ws://${host}:${ROSBRIDGE_PORT}`;
    if (!out.includes(u)) out.push(u);
  };
  if (typeof window !== "undefined" && window.location?.hostname) {
    add(window.location.hostname);
  }
  add("127.0.0.1");
  add("localhost");
  return out;
}

class RosBridge {
  /**
   * @param {string | null | undefined} explicitUrl Si se omite, se prueban candidatos en connect().
   */
  constructor(explicitUrl) {
    this._explicitUrl =
      explicitUrl !== undefined && explicitUrl !== null && explicitUrl !== ""
        ? explicitUrl
        : null;
    this.url = this._explicitUrl || "";
    /** @type {ROSLIB.Ros | null} */
    this.ros = null;
    this._connected = false;
    /** Evita el mensaje de “stack detenido” al usar disconnect() manual. */
    this._suppressClosedLog = false;
    /** @type {Array<(s: string) => void>} */
    this._statusCbs = [];
    /** @type {ReturnType<typeof setTimeout> | null} */
    this._connectTimer = null;
  }

  connect() {
    if (typeof ROSLIB === "undefined") {
      console.error("roslib not loaded");
      this._emitStatus("error");
      return;
    }
    const urls = this._explicitUrl
      ? [this._explicitUrl]
      : rosbridgeWebSocketCandidates();
    this._connectAttempt(urls, 0);
  }

  /**
   * @param {string[]} urls
   * @param {number} i
   */
  _connectAttempt(urls, i) {
    if (this._connectTimer !== null) {
      clearTimeout(this._connectTimer);
      this._connectTimer = null;
    }
    if (i >= urls.length) {
      console.error("rosbridge: sin conexión tras probar:", urls.join(", "));
      this._emitStatus("error");
      return;
    }
    this.url = urls[i];
    if (this.ros) {
      try {
        this.ros.close();
      } catch (_) {}
      this.ros = null;
    }

    let connecting = true;
    /** Salimos de este intento (éxito o paso al siguiente URL). */
    let handshakeDone = false;
    /** Hubo evento "connection" en este intento. */
    let connectedOk = false;

    const tryNext = () => {
      if (handshakeDone) return;
      handshakeDone = true;
      connecting = false;
      if (this._connectTimer !== null) {
        clearTimeout(this._connectTimer);
        this._connectTimer = null;
      }
      if (this.ros) {
        try {
          this.ros.close();
        } catch (_) {}
        this.ros = null;
      }
      this._connectAttempt(urls, i + 1);
    };

    this.ros = new ROSLIB.Ros({ url: this.url });

    this._connectTimer = setTimeout(() => {
      if (connecting && !handshakeDone) tryNext();
    }, 2500);

    this.ros.on("connection", () => {
      if (handshakeDone) return;
      handshakeDone = true;
      connectedOk = true;
      connecting = false;
      if (this._connectTimer !== null) {
        clearTimeout(this._connectTimer);
        this._connectTimer = null;
      }
      this._connected = true;
      this._emitStatus("connected");
    });

    this.ros.on("error", () => {
      if (!connectedOk) {
        if (!handshakeDone) tryNext();
        return;
      }
      this._connected = false;
      this._emitStatus("error");
    });

    this.ros.on("close", () => {
      connecting = false;
      if (this._connectTimer !== null) {
        clearTimeout(this._connectTimer);
        this._connectTimer = null;
      }
      this._connected = false;
      if (!connectedOk && !handshakeDone) {
        tryNext();
        return;
      }
      if (!connectedOk) {
        return;
      }
      this._emitStatus("closed");
      if (
        !this._suppressClosedLog &&
        typeof window !== "undefined" &&
        typeof window.testbenchLog === "function"
      ) {
        window.testbenchLog(
          "Stack detenido. Ejecuta testbench/run_all.sh para reiniciar."
        );
      }
      this._suppressClosedLog = false;
    });
  }

  get connected() {
    return this._connected && this.ros !== null;
  }

  on_status(cb) {
    this._statusCbs.push(cb);
  }

  _emitStatus(s) {
    this._statusCbs.forEach((cb) => {
      try {
        cb(s);
      } catch (_) {}
    });
  }

  /**
   * @returns {() => void} unsubscribe
   */
  subscribe(topic, type, cb) {
    if (!this.ros) throw new Error("Ros not initialized");
    const t = new ROSLIB.Topic({
      ros: this.ros,
      name: topic,
      messageType: type,
      throttle_rate: 0,
    });
    const fn = (msg) => {
      try {
        cb(msg);
      } catch (e) {
        console.error(topic, e);
      }
    };
    t.subscribe(fn);
    return () => {
      try {
        t.unsubscribe(fn);
        t.dispose && t.dispose();
      } catch (_) {}
    };
  }

  publish(topic, type, msg) {
    if (!this.ros) throw new Error("Ros not initialized");
    const pub = new ROSLIB.Topic({
      ros: this.ros,
      name: topic,
      messageType: type,
    });
    const m = new ROSLIB.Message(msg);
    pub.publish(m);
  }

  /** Cierra el WebSocket hacia rosbridge (no apaga nodos ROS). */
  disconnect() {
    if (this._connectTimer !== null) {
      clearTimeout(this._connectTimer);
      this._connectTimer = null;
    }
    this._suppressClosedLog = true;
    if (this.ros) {
      try {
        this.ros.close();
      } catch (_) {}
    }
    this._connected = false;
    this.ros = null;
  }

  call_service(name, type, req, cb) {
    if (!this.ros) throw new Error("Ros not initialized");
    const srv = new ROSLIB.Service({
      ros: this.ros,
      name,
      serviceType: type,
    });
    const rq = new ROSLIB.ServiceRequest(req);
    srv.callService(rq, (res) => {
      try {
        cb && cb(null, res);
      } catch (e) {
        cb && cb(e);
      }
    });
  }
}

window.RosBridge = RosBridge;
window.rosbridgeWebSocketCandidates = rosbridgeWebSocketCandidates;
