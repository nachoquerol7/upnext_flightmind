/**
 * Semáforos de nodos + FDIR (M6).
 */
class WatchdogPanel extends BasePanel {
  mount() {
    this.container.innerHTML = "";
    this._nodes = [
      { id: "mission_fsm_node", topic: "/fsm/state", label: "mission_fsm" },
      { id: "daidalus_node", topic: "/daidalus/alert_level", label: "daidalus" },
      { id: "fdir_node", topic: "/fdir/status", label: "fdir" },
      { id: "nav2_adapter", topic: "/nav/quality_flag", label: "nav2" },
    ];
    this._lastMsg = {};
    const grid = document.createElement("div");
    grid.className = "watchdog-grid";
    this._nodes.forEach((n) => {
      const card = document.createElement("div");
      card.className = "watchdog-card";
      card.dataset.node = n.id;
      card.innerHTML = `
        <div class="wd-title">${n.label}</div>
        <div class="wd-hb"><span class="wd-dot">●</span></div>
        <div class="wd-age">— ms</div>
        <div class="wd-state">STALE</div>
      `;
      grid.appendChild(card);
    });
    this.container.appendChild(grid);
    const banner = document.createElement("div");
    banner.className = "watchdog-banner";
    banner.classList.add("wd-banner-el");
    banner.style.display = "none";
    banner.textContent = "WATCHDOG TRIGGERED";
    this.container.appendChild(banner);
    const emerg = document.createElement("div");
    emerg.className = "fdir-emergency-banner";
    emerg.classList.add("fdir-emerg-el");
    emerg.style.display = "none";
    emerg.textContent = "FDIR EMERGENCY";
    this.container.appendChild(emerg);
    const tree = document.createElement("div");
    tree.className = "wd-consequence";
    tree.classList.add("wd-tree-el");
    tree.innerHTML =
      "<b>Árbol de consecuencias</b> (placeholder): si un nodo está DEAD, las transiciones FSM que dependen de él no pueden completarse.";
    this.container.appendChild(tree);

    const stamp = () => Date.now();
    this._nodes.forEach((n) => {
      const t = n.topic;
      const typ =
        t === "/fsm/state"
          ? "flightmind_msgs/FSMState"
          : t === "/daidalus/alert_level"
            ? "std_msgs/Int32"
            : t === "/fdir/status"
              ? "std_msgs/String"
              : "std_msgs/Float64";
      this.subscribeRos(t, typ, () => {
        this._lastMsg[n.id] = stamp();
      });
    });
    this.subscribeRos("/fdir/emergency", "std_msgs/Bool", (msg) => {
      if (msg && msg.data) this._flashEmergency();
    });
    this.subscribeRos("/fdir/active_fault", "std_msgs/String", (msg) => {
      if (msg && msg.data) this._applyActiveFault(String(msg.data));
    });
  }

  _flashEmergency() {
    const el = this.container.querySelector(".fdir-emerg-el");
    if (el) {
      el.style.display = "block";
      setTimeout(() => {
        if (el) el.style.display = "none";
      }, 1000);
    }
    this.container.querySelectorAll(".watchdog-card").forEach((c) => {
      c.classList.add("wd-flash");
      setTimeout(() => c.classList.remove("wd-flash"), 1000);
    });
  }

  _applyActiveFault(fault) {
    this.container.querySelectorAll(".watchdog-card").forEach((c) => {
      c.classList.remove("wd-fault");
    });
    const match = this._nodes.find((n) => fault.indexOf(n.label) >= 0);
    if (match) {
      const card = this.container.querySelector(`[data-node="${match.id}"]`);
      if (card) {
        card.classList.add("wd-fault");
        const title = card.querySelector(".wd-title");
        if (title) title.textContent = match.label + " · " + fault;
      }
    }
  }

  handleTopic(topic, msg) {
    const now = Date.now();
    this._nodes.forEach((n) => {
      if (n.topic === topic) {
        this._lastMsg[n.id] = now;
      }
    });
    if (topic === "/fdir/emergency" && msg && msg.data) {
      this._flashEmergency();
    }
    if (topic === "/fdir/active_fault" && msg && msg.data) {
      this._applyActiveFault(String(msg.data));
    }
  }

  syncFromState(st) {
    if (this._frozen) return;
    const now = Date.now();
    this._nodes.forEach((n) => {
      const card = this.container.querySelector(`[data-node="${n.id}"]`);
      if (!card) return;
      const last = this._lastMsg[n.id];
      const age = last != null ? now - last : 1e9;
      const dot = card.querySelector(".wd-dot");
      const ageEl = card.querySelector(".wd-age");
      const stEl = card.querySelector(".wd-state");
      if (ageEl) ageEl.textContent = last != null ? age + " ms" : "sin mensajes";
      let state = "DEAD";
      let cls = "wd-dead";
      if (last != null && age < 500) {
        state = "ALIVE";
        cls = "wd-alive";
      } else if (last != null && age < 3000) {
        state = "STALE";
        cls = "wd-stale";
      }
      if (dot) dot.className = "wd-dot " + cls;
      if (stEl) {
        stEl.textContent = state;
        stEl.className = "wd-state " + cls;
      }
      card.classList.toggle("wd-card-dead", state === "DEAD");
    });
    const banner = this.container.querySelector(".wd-banner-el");
    if (banner) {
      const anyDead = this._nodes.some((n) => {
        const last = this._lastMsg[n.id];
        return last == null || now - last > 3000;
      });
      banner.style.display = anyDead ? "block" : "none";
    }
  }
}

window.WatchdogPanel = WatchdogPanel;
