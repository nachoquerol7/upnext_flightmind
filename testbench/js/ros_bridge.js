/**
 * ROS2 bridge via rosbridge WebSocket + roslibjs
 * @see https://github.com/RobotWebTools/roslibjs
 */
class RosBridge {
  constructor(url = "ws://localhost:9090") {
    this.url = url;
    /** @type {ROSLIB.Ros | null} */
    this.ros = null;
    this._connected = false;
    /** @type {Array<(s: string) => void>} */
    this._statusCbs = [];
  }

  connect() {
    if (typeof ROSLIB === "undefined") {
      console.error("roslib not loaded");
      this._emitStatus("error");
      return;
    }
    if (this.ros) {
      try {
        this.ros.close();
      } catch (_) {}
    }
    this.ros = new ROSLIB.Ros({ url: this.url });
    this.ros.on("connection", () => {
      this._connected = true;
      this._emitStatus("connected");
    });
    this.ros.on("error", () => {
      this._connected = false;
      this._emitStatus("error");
    });
    this.ros.on("close", () => {
      this._connected = false;
      this._emitStatus("closed");
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
