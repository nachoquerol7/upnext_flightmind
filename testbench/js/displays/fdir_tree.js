/**
 * FDIR fault tree — highlights nodes from /fdir/active_fault string match
 */
const FdirTree = {
  svg: null,
  mount(parent) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <h2 class="section-title">FDIR — árbol de fallos</h2>
      <svg id="fdir-svg" width="100%" height="220" viewBox="0 0 520 220" style="background:#0a1628;border-radius:8px;border:1px solid #1e3a52;"></svg>
      <div id="fdir-status-txt" style="margin-top:8px;font-size:11px;color:#b8d4f0;">/fdir/status: —</div>
      <div id="fdir-log" style="margin-top:6px;max-height:80px;overflow:auto;font-size:10px;color:#8aa4bc;"></div>
    `;
    parent.appendChild(wrap);
    this.svg = document.getElementById("fdir-svg");
    this._buildSvg();
  },

  _buildSvg() {
    const ns = "http://www.w3.org/2000/svg";
    const svg = this.svg;
    const nodes = [
      { id: "SYSTEM", x: 260, y: 40, w: 90, h: 28 },
      { id: "NAV", x: 80, y: 120, w: 70, h: 24 },
      { id: "POWER", x: 180, y: 120, w: 70, h: 24 },
      { id: "LINK", x: 280, y: 120, w: 70, h: 24 },
      { id: "AVIONICS", x: 380, y: 120, w: 80, h: 24 },
    ];
    const line = (x1, y1, x2, y2) => {
      const l = document.createElementNS(ns, "line");
      l.setAttribute("x1", x1);
      l.setAttribute("y1", y1);
      l.setAttribute("x2", x2);
      l.setAttribute("y2", y2);
      l.setAttribute("stroke", "#3a5a72");
      l.setAttribute("stroke-width", "2");
      svg.appendChild(l);
    };
    line(260, 68, 115, 108);
    line(260, 68, 215, 108);
    line(260, 68, 315, 108);
    line(260, 68, 420, 108);
    nodes.forEach((n) => {
      const g = document.createElementNS(ns, "g");
      g.setAttribute("data-fdir", n.id);
      const r = document.createElementNS(ns, "rect");
      r.setAttribute("x", n.x - n.w / 2);
      r.setAttribute("y", n.y - n.h / 2);
      r.setAttribute("width", n.w);
      r.setAttribute("height", n.h);
      r.setAttribute("rx", "6");
      r.setAttribute("fill", "#16334a");
      r.setAttribute("stroke", "#4a6a88");
      const t = document.createElementNS(ns, "text");
      t.setAttribute("x", n.x);
      t.setAttribute("y", n.y + 4);
      t.setAttribute("text-anchor", "middle");
      t.setAttribute("fill", "#e0e8f0");
      t.setAttribute("font-size", "10px");
      t.setAttribute("font-family", "monospace");
      t.textContent = n.id;
      g.appendChild(r);
      g.appendChild(t);
      svg.appendChild(g);
    });
  },

  update(st) {
    const emerg = st.fdirEmergency === true;
    const active = (st.fdirActiveFault && String(st.fdirActiveFault)) || "";
    const stat = st.fdirStatus || "—";
    const el = document.getElementById("fdir-status-txt");
    if (el) el.textContent = "/fdir/status: " + stat;

    ["SYSTEM", "NAV", "POWER", "LINK", "AVIONICS"].forEach((id) => {
      const g = this.svg.querySelector(`[data-fdir="${id}"]`);
      if (!g) return;
      const r = g.querySelector("rect");
      let on = emerg && id === "SYSTEM";
      if (active && active.toUpperCase().indexOf(id) >= 0) on = true;
      if (active && id === "NAV" && /NAV|LOC|GPS|ODOM/i.test(active)) on = true;
      r.setAttribute("fill", on ? "#8b2a2a" : "#16334a");
      r.setAttribute("stroke", on ? "#ff5252" : "#4a6a88");
    });

    if (st._fdirEvent) {
      const log = document.getElementById("fdir-log");
      if (log) {
        log.innerHTML =
          `<div>${st._fdirEvent}</div>` + log.innerHTML.split("</div>").slice(0, 8).join("</div>");
      }
    }
  },
};

window.FdirTree = FdirTree;
