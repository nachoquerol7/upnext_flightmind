/**
 * SVG FSM graph — 9 states from mission FSM YAML
 */
const FSM_LAYOUT = [
  { id: "PREFLIGHT", x: 80, y: 220 },
  { id: "AUTOTAXI", x: 200, y: 120 },
  { id: "TAKEOFF", x: 340, y: 120 },
  { id: "CRUISE", x: 480, y: 120 },
  { id: "EVENT", x: 480, y: 260 },
  { id: "LANDING", x: 620, y: 120 },
  { id: "GO_AROUND", x: 620, y: 260 },
  { id: "RTB", x: 340, y: 320 },
  { id: "ABORT", x: 200, y: 320 },
];

const FSM_EDGES = [
  ["PREFLIGHT", "AUTOTAXI"],
  ["AUTOTAXI", "TAKEOFF"],
  ["TAKEOFF", "CRUISE"],
  ["CRUISE", "EVENT"],
  ["CRUISE", "LANDING"],
  ["CRUISE", "RTB"],
  ["LANDING", "GO_AROUND"],
  ["EVENT", "CRUISE"],
  ["EVENT", "ABORT"],
  ["ABORT", "RTB"],
];

const FSM_COLORS = {
  PREFLIGHT: "#607d8b",
  AUTOTAXI: "#80cbc4",
  TAKEOFF: "#00bcd4",
  CRUISE: "#00e676",
  EVENT: "#ffab40",
  LANDING: "#69f0ae",
  GO_AROUND: "#ce93d8",
  RTB: "#ff8f00",
  ABORT: "#ff5252",
};

const FsmGraph = {
  container: null,
  lastMode: "",
  activeEdge: null,
  edgeUntil: 0,
  mount(parent) {
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    this.container = document.createElement("div");
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "320");
    svg.setAttribute("viewBox", "0 0 760 380");
    svg.style.background = "#0a1628";
    svg.style.borderRadius = "8px";
    svg.style.border = "1px solid #1e3a52";

    FSM_EDGES.forEach(([a, b]) => {
      const na = FSM_LAYOUT.find((n) => n.id === a);
      const nb = FSM_LAYOUT.find((n) => n.id === b);
      if (!na || !nb) return;
      const line = document.createElementNS(svgNS, "line");
      line.setAttribute("x1", na.x);
      line.setAttribute("y1", na.y);
      line.setAttribute("x2", nb.x);
      line.setAttribute("y2", nb.y);
      line.setAttribute("stroke", "#2a4a66");
      line.setAttribute("stroke-width", "2");
      line.setAttribute("data-edge", a + "->" + b);
      svg.appendChild(line);
    });

    FSM_LAYOUT.forEach((n) => {
      const g = document.createElementNS(svgNS, "g");
      g.setAttribute("data-node", n.id);
      const c = document.createElementNS(svgNS, "circle");
      c.setAttribute("cx", n.x);
      c.setAttribute("cy", n.y);
      c.setAttribute("r", "28");
      c.setAttribute("fill", FSM_COLORS[n.id] || "#666");
      c.setAttribute("stroke", "#1a3344");
      c.setAttribute("stroke-width", "2");
      const t = document.createElementNS(svgNS, "text");
      t.setAttribute("x", n.x);
      t.setAttribute("y", n.y + 4);
      t.setAttribute("text-anchor", "middle");
      t.setAttribute("fill", "#0a1628");
      t.setAttribute("font-size", "9px");
      t.setAttribute("font-family", "monospace");
      t.textContent = n.id.length > 8 ? n.id.slice(0, 7) + "…" : n.id;
      g.appendChild(c);
      g.appendChild(t);
      svg.appendChild(g);
    });

    this.svg = svg;
    this.container.appendChild(svg);
    const meta = document.createElement("div");
    meta.id = "fsm-meta";
    meta.style.marginTop = "8px";
    meta.style.fontSize = "11px";
    meta.style.color = "#b8d4f0";
    this.container.appendChild(meta);
    parent.appendChild(this.container);
  },

  update(st) {
    const mode = (st.fsmState && st.fsmState.current_mode) || st.legacyMode || "";
    const trig = (st.fsmState && st.fsmState.active_trigger) || "—";
    const sub = (st.fsmState && st.fsmState.event_substate) || "—";
    const meta = document.getElementById("fsm-meta");
    if (meta) {
      meta.innerHTML = `<div><b>current_mode</b>: ${mode || "—"}</div><div><b>active_trigger</b>: ${trig}</div><div><b>event_substate</b>: ${sub}</div>`;
    }
    if (mode && mode !== this.lastMode) {
      if (this.lastMode) {
        this.activeEdge = [this.lastMode, mode];
        this.edgeUntil = Date.now() + 600;
      }
      this.lastMode = mode;
    }
    const active = mode;
    FSM_LAYOUT.forEach((n) => {
      const g = this.svg.querySelector(`[data-node="${n.id}"]`);
      if (!g) return;
      const c = g.querySelector("circle");
      const on = n.id === active;
      c.setAttribute("stroke", on ? "#ffffff" : "#1a3344");
      c.setAttribute("stroke-width", on ? "4" : "2");
      c.setAttribute("filter", on ? "drop-shadow(0 0 6px #fff)" : "");
    });

    const hiEdge = Date.now() < this.edgeUntil && this.activeEdge;
    FSM_EDGES.forEach(([a, b]) => {
      const line = this.svg.querySelector(`line[data-edge="${a}->${b}"]`);
      if (!line) return;
      const hit = hiEdge && hiEdge[0] === a && hiEdge[1] === b;
      line.setAttribute("stroke", hit ? "#4a9eff" : "#2a4a66");
      line.setAttribute("stroke-width", hit ? "4" : "2");
    });
  },
};

window.FsmGraph = FsmGraph;
window.FSM_COLORS = FSM_COLORS;
