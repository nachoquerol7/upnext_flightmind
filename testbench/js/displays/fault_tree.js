/**
 * E2E fault cascade — placeholder (visible)
 */
const FaultTreeDisplay = {
  mount(parent) {
    const d = document.createElement("div");
    d.className = "placeholder-box";
    d.innerHTML =
      "<b>M10 E2E — fault cascade</b><br/>Display pendiente: cascada de fallos end-to-end.<br/>Conectar topics de misión / black-box cuando estén disponibles.";
    parent.appendChild(d);
  },
  update() {},
};

window.FaultTreeDisplay = FaultTreeDisplay;
