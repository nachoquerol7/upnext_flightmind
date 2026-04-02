/**
 * Definiciones V&V SIL — metadatos por TC (252 entradas) + agrupación por módulo.
 * Los `steps` se rellenan en TC_STEPS (mismo archivo, sección inferior) o vía legacy modules.
 */
(function () {
  "use strict";

  /** @typedef {Object} TcDefinition */
  /** @typedef {{ key: string, title: string, prefix: string, start: number, end: number, panel: string, required_panels?: string[] }} ModuleRange */

  /** @type {ModuleRange[]} */
  const RANGES = [
    {
      key: "M1",
      title: "M1 — FSM Transitions",
      prefix: "TC-FSM-",
      start: 1,
      end: 30,
      panel: "FsmGraphPanel",
      required_panels: ["FsmGraphPanel", "HysteresisPanel"],
    },
    {
      key: "M2",
      title: "M2 — Timeouts / temporal",
      prefix: "TC-TO-",
      start: 1,
      end: 10,
      panel: "FsmGraphPanel",
      required_panels: ["FsmGraphPanel", "HysteresisPanel"],
    },
    {
      key: "M3",
      title: "M3 — Integridad YAML / FSM",
      prefix: "TC-INT-",
      start: 1,
      end: 12,
      panel: "FsmGraphPanel",
      required_panels: ["FsmGraphPanel", "HysteresisPanel"],
    },
    {
      key: "M4",
      title: "M4 — Histéresis / umbrales",
      prefix: "TC-HYS-",
      start: 1,
      end: 7,
      panel: "FsmGraphPanel",
      required_panels: ["FsmGraphPanel", "HysteresisPanel"],
    },
    {
      key: "M5",
      title: "M5 — Localización / quality",
      prefix: "TC-LOC-",
      start: 1,
      end: 13,
      panel: "MapPanel",
      required_panels: ["MapPanel", "HysteresisPanel"],
    },
    {
      key: "M6",
      title: "M6 — DAIDALUS / DAA",
      prefix: "TC-DAI-",
      start: 1,
      end: 12,
      panel: "RadarPanel",
      required_panels: ["RadarPanel", "MapPanel"],
    },
    {
      key: "M7",
      title: "M7 — FDIR / watchdog",
      prefix: "TC-FDIR-",
      start: 1,
      end: 16,
      panel: "WatchdogPanel",
      required_panels: ["WatchdogPanel", "HysteresisPanel"],
    },
    {
      key: "M8",
      title: "M8 — Navegación / Nav2",
      prefix: "TC-NAV-",
      start: 1,
      end: 12,
      panel: "MapPanel",
      required_panels: ["MapPanel", "GppRrtPanel"],
    },
    {
      key: "M9",
      title: "M9 — Middleware ROS2",
      prefix: "TC-MW-",
      start: 1,
      end: 10,
      panel: "LatencyPanel",
      required_panels: ["LatencyPanel", "HysteresisPanel"],
    },
    {
      key: "M10",
      title: "M10 — E2E nominal",
      prefix: "TC-E2E-",
      start: 1,
      end: 10,
      panel: "E2EPanel",
      required_panels: ["E2EPanel"],
    },
    {
      key: "M11",
      title: "M11 — Fallos / recuperación",
      prefix: "TC-FAULT-",
      start: 1,
      end: 12,
      panel: "E2EPanel",
      required_panels: ["E2EPanel", "WatchdogPanel"],
    },
    {
      key: "M12",
      title: "M12 — Rendimiento",
      prefix: "TC-PERF-",
      start: 1,
      end: 8,
      panel: "LatencyPanel",
      required_panels: ["LatencyPanel", "FsmGraphPanel"],
    },
    {
      key: "GPP-M1",
      title: "GPP-M1 — Flight levels",
      prefix: "TC-FL-",
      start: 1,
      end: 13,
      panel: "MapPanel",
      required_panels: ["GppRrtPanel", "MapPanel"],
    },
    {
      key: "GPP-M2",
      title: "GPP-M2 — Geometría / corridor",
      prefix: "TC-GEO-",
      start: 1,
      end: 12,
      panel: "MapPanel",
      required_panels: ["MapPanel", "GppRrtPanel"],
    },
    {
      key: "GPP-M3",
      title: "GPP-M3 — Dubins",
      prefix: "TC-DUB-",
      start: 1,
      end: 11,
      panel: "MapPanel",
      required_panels: ["GppRrtPanel", "MapPanel"],
    },
    {
      key: "GPP-M4",
      title: "GPP-M4 — Informed-RRT*",
      prefix: "TC-RRT-",
      start: 1,
      end: 12,
      panel: "MapPanel",
      required_panels: ["GppRrtPanel", "MapPanel"],
    },
    {
      key: "GPP-M5",
      title: "GPP-M5 — Planificación temporal",
      prefix: "TC-GTO-",
      start: 1,
      end: 12,
      panel: "MapPanel",
      required_panels: ["MapPanel", "GppRrtPanel"],
    },
    {
      key: "GPP-M6",
      title: "GPP-M6 — Nodos / grafo",
      prefix: "TC-NODE-",
      start: 1,
      end: 10,
      panel: "MapPanel",
      required_panels: ["GppRrtPanel", "MapPanel"],
    },
    {
      key: "GPP-M7",
      title: "GPP-M7 — Integración GPP",
      prefix: "TC-GPPI-",
      start: 1,
      end: 5,
      panel: "MapPanel",
      required_panels: ["GppRrtPanel", "MapPanel", "HysteresisPanel"],
    },
    {
      key: "GPP-M8",
      title: "GPP-M8 — Requisitos SR-GPP",
      prefix: "SR-GPP-",
      start: 1,
      end: 8,
      panel: "MapPanel",
      required_panels: ["MapPanel", "GppRrtPanel"],
    },
    {
      key: "AUX",
      title: "AUX — Cobertura plan maestro",
      prefix: "TC-AUX-",
      start: 1,
      end: 17,
      panel: "FsmGraphPanel",
      required_panels: ["FsmGraphPanel", "HysteresisPanel"],
    },
  ];

  const PAD = (n, w) => String(n).padStart(w, "0");

  /** Títulos explícitos (subset); el resto usa plantilla por prefijo. */
  const TITLE_OVERRIDES = {
    "TC-FSM-001": "PREFLIGHT → AUTOTAXI por preflight_ok",
    "TC-FSM-002": "AUTOTAXI → TAKEOFF por taxi_clear",
    "TC-FSM-003": "TAKEOFF → CRUISE por takeoff_complete",
    "TC-FSM-004": "CRUISE → EVENT por quality_degraded",
    "TC-FSM-005": "CRUISE → RTB por rtb_command",
    "TC-FSM-006": "CRUISE → LANDING por land_command",
    "TC-FSM-007": "EVENT → CRUISE por event_cleared",
    "TC-FSM-008": "CRUISE → ABORT por fdir_emergency",
    "TC-DAI-001": "Alerta ámbar → EVENT",
    "TC-DAI-002": "Alerta bajo umbral mantiene CRUISE",
    "TC-FDIR-001": "Emergencia FDIR → escalado",
    "TC-E2E-001": "Secuencia nominal PREFLIGHT→CRUISE",
    "TC-FAULT-001": "Waypoint persistencia / resume",
    "TC-PERF-001": "Latencia transición FSM p99",
  };

  const XFAIL_BY_PREFIX = {
    "TC-TO-": "ARCH-1.2 / ARCH-1.7 (timeouts de morada y supervisión externa)",
  };

  function defaultTitle(id, prefix) {
    if (TITLE_OVERRIDES[id]) return TITLE_OVERRIDES[id];
    if (id.startsWith("SR-GPP-")) return `Requisito de seguridad GPP ${id}`;
    return `Caso de prueba ${id} (${prefix.replace(/-$/, "")})`;
  }

  function defaultWhat(id, mod) {
    return `Validación SIL del criterio ${id} en el subsistema ${mod.title}. Consultar UAS_SIL_VnV_Plan_v2 y mission_fsm / gpp según módulo.`;
  }

  function buildDefinition(id, mod, num) {
    let xfailReason = null;
    for (const [pref, reason] of Object.entries(XFAIL_BY_PREFIX)) {
      if (id.startsWith(pref)) {
        xfailReason = reason;
        break;
      }
    }
    const reqPanels =
      mod.required_panels && mod.required_panels.length ? [...mod.required_panels] : [mod.panel];
    return {
      id,
      title: defaultTitle(id, mod.prefix),
      priority: id.startsWith("TC-FSM-0") && parseInt(id.split("-").pop(), 10) <= 10 ? "P0" : "P1",
      module: mod.key,
      moduleTitle: mod.title,
      what: defaultWhat(id, mod),
      params: [`${id}`, `panel=${mod.panel}`, `required_panels=${reqPanels.join(",")}`],
      oracle: `Criterios del plan V&V para ${id}: estados / topics según especificación del módulo.`,
      pass_visual: "Indicadores PASS y animación acorde al panel activo.",
      fail_visual: "Estado estable incorrecto o timeout del oráculo.",
      references: ["UAS_SIL_VnV_Plan_v2.pdf", "docs/vnv/XFAIL_INDEX.md"],
      xfail: xfailReason,
      panel: mod.panel,
      required_panels: reqPanels,
      steps: [],
    };
  }

  function generateAllDefinitions() {
    /** @type {Record<string, TcDefinition>} */
    const out = {};
    for (const mod of RANGES) {
      const w = mod.prefix.includes("SR-") ? 3 : 3;
      for (let n = mod.start; n <= mod.end; n++) {
        const id = mod.prefix + PAD(n, w);
        out[id] = buildDefinition(id, mod, n);
      }
    }
    return out;
  }

  const TC_DEFINITIONS = generateAllDefinitions();

  /** Metadatos enriquecidos (ejemplos del plan V&V). */
  const METADATA_PATCHES = {
    "TC-FSM-001": {
      what: "La transición inicial del FSM cuando todos los checks pre-vuelo pasan.",
      params: ["preflight_ok=True", "/fsm/state.current_mode", "trigger='to_autotaxi'"],
      oracle: "FSM.current_mode == 'AUTOTAXI' en < 1 tick (100ms). active_trigger == 'to_autotaxi'.",
      pass_visual: "Nodo AUTOTAXI iluminado en teal. active_trigger visible en barra inferior.",
      fail_visual: "PREFLIGHT sigue activo tras 3000ms. trigger vacío.",
      references: ["SR-FSM-01", "UAS_SIL_VnV_Plan_v2.pdf §M1"],
    },
    "TC-DAI-001": {
      required_panels: ["RadarPanel", "MapPanel"],
    },
    "TC-DAI-002": {
      required_panels: ["RadarPanel", "MapPanel"],
    },
    "TC-FSM-004": {
      what: "Cuando quality_flag cae bajo el umbral (0.5), el FSM debe entrar en EVENT en ≤ 2 ticks.",
      params: ["quality_flag < 0.5", "quality_flag_threshold=0.5", "trigger='to_event'"],
      oracle: "FSM.current_mode == 'EVENT' en ≤ 200ms. active_trigger == 'to_event'.",
      pass_visual: "Nodo EVENT en ámbar; quality en barra roja.",
      fail_visual: "Permanece CRUISE con quality bajo.",
      references: ["SR-FSM-01", "SR-NAV-02", "UAS_SIL_VnV_Plan_v2.pdf §M1"],
    },
    "TC-FSM-006": {
      what: "Desde CRUISE, land_command debe llevar a LANDING con trigger coherente.",
      params: ["land_command=True", "/fsm/state.current_mode", "trigger hacia LANDING"],
      oracle: "FSM.current_mode == 'LANDING' en el timeout del paso. Comando de aterrizaje reconocido.",
      pass_visual: "Nodo LANDING activo; trayectoria de descenso en panel si disponible.",
      fail_visual: "CRUISE sin cambio tras comando.",
      references: ["UAS_SIL_VnV_Plan_v2.pdf §M1", "SR-FSM-01"],
    },
  };
  for (const [tid, patch] of Object.entries(METADATA_PATCHES)) {
    if (TC_DEFINITIONS[tid]) Object.assign(TC_DEFINITIONS[tid], patch);
  }

  /** Pasos ejecutables por TC (ampliado en fases; legacy completa M1 corto). */
  const TC_STEPS = {};

  window.TC_DEFINITIONS = TC_DEFINITIONS;
  window.TC_STEPS = TC_STEPS;
  window.TC_DEFINITION_RANGES = RANGES;

  /**
   * Fusiona steps desde módulos legacy (M1FSM, …) si existen.
   */
  window.collectLegacySteps = function collectLegacySteps() {
    /** @type {Record<string, unknown[]>} */
    const map = {};
    const mods = [
      window.M1FSM,
      window.M2INT,
      window.M4LOC,
      window.M5DAI,
      window.M6FDIR,
      window.M7NAV,
      window.M8MW,
      window.M9E2E,
      window.M10FLT,
    ];
    for (const m of mods) {
      if (!m || !m.tcs) continue;
      for (const tc of m.tcs) {
        if (tc.id && tc.steps) map[tc.id] = tc.steps;
      }
    }
    return map;
  };

  /**
   * @returns {{ id: string, title: string, tcs: object[] }[]}
   */
  window.getModulesForSidebar = function getModulesForSidebar() {
    const legacy = window.collectLegacySteps();
    const modules = [];

    for (const mod of RANGES) {
      const w = mod.prefix.includes("SR-") ? 3 : 3;
      const tcs = [];
      for (let n = mod.start; n <= mod.end; n++) {
        const id = mod.prefix + PAD(n, w);
        const def = TC_DEFINITIONS[id];
        if (!def) continue;
        const steps = TC_STEPS[id] || legacy[id] || def.steps || [];
        tcs.push({
          id: def.id,
          name: def.title,
          title: def.title,
          module: def.module,
          steps,
          definition: def,
        });
      }
      modules.push({ id: mod.key, title: mod.title, tcs });
    }
    return modules;
  };

  window.getTcDefinition = function getTcDefinition(id) {
    return TC_DEFINITIONS[id] || null;
  };
})();
