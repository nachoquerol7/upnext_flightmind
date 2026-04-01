# Roadmap de autonomía UAS (SIRTAP / Flightmind)

Plan por fases **sin saltos** (de menor a mayor complejidad). Los paquetes esqueleto en `src/` corresponden a las carpetas previstas; la implementación sigue el orden de fases.

| Fase | Contenido | Días (est.) |
|------|-----------|-------------|
| 0 | Limpieza + estructura + dependencias | 1–2 |
| 1 | Vehicle Model | 2–3 |
| 2 | FSM de misión | 3–4 |
| 3 | FDIR | 3–4 |
| 4 | DAIDALUS + PolyCARP como nodos ROS 2 | 4–5 |
| 5 | GPP: FL + Informed-RRT\* + Takeoff/Landing | 5–7 |
| 6 | Replanificador local | 4–5 |
| 7 | Trayectoria Dubins ejecutable | 2–3 |
| 8 | ACAS Xu RT | 2–3 |
| 9 | Integración E2E + V&V | 5–7 |

**Total orientativo:** 31–43 días (paralelizando bloques independientes ~3–4 semanas si la integración va bien). Cuellos: Fase 5 (GPP) y Fase 9 (E2E).

---

## Fase 0 — Limpieza y base

- Cerrar línea **ICAROUS+cFS** para desarrollo nuevo: scripts viejos en `archive/icarous_cfs_legacy/` (ver README allí). `scripts/setup_icarous_env.sh` falla a propósito con mensaje de deprecación.
- **PX4 SITL:** verificar localmente `make px4_sitl_default jmavsim` (y multirrotor si aplica) en tu árbol PX4.
- **Dependencias:** `docs/DEPENDENCIES_PHASE0.md` y `scripts/install_deps_phase0.sh`.
- **Estructura `src/` (entregable Fase 0):**
  - `vehicle_model`, `mission_fsm`, `fdir`, `gpp`, `daidalus_node`, `polycarp_node`, `local_replanner`, `trajectory_gen`, `acas_node`, `uas_stack_tests`
- Paquetes legacy conservados: `upnext_icarous_*`, `upnext_airspace`, `upnext_bringup`.

---

## Fase 1 — Vehicle Model

Clase con YAML (`v_min_ms`, `v_max_ms`, `turn_radius_min_m`, climb/descent, glide, peso, fuel burn), `update_weight()`, `is_feasible()`, topic latched `/vehicle_model/state`, tests pytest (combustible, radio de giro, climb rechazado).

---

## Fase 2 — FSM de misión

Estados: PREFLIGHT → AUTOTAXI → TAKEOFF → CRUISE → EVENT → LANDING → GO_AROUND → ABORT → RTB. Topics `/fsm/current_mode`, `/fsm/active_trigger`. Tests: una función por transición crítica (CRUISE→EVENT, EVENT→ABORT, LANDING→GO_AROUND, …).

---

## Fase 3 — FDIR

Suscripciones IMU, vehicle model, quality flag, vehicle status. Detectores: NavDegraded, MotorLoss, SensorTimeout, LinkLoss. Árbol YAML → `/fdir/active_fault`, `/fdir/policy_action`. Tests con fallos inyectados.

---

## Fase 4 — DAIDALUS + PolyCARP (ROS 2)

Nodo C++ DAIDALUS: ownship + intrusos → bandas, alert level, resolution advisory. Nodo Python PolyCARP: geofences → violación inminente + tiempo. YAML SIRTAP (lookahead, alerting, DMOD, ZTHR, turn rate). Validación vs casos NASA DO-365. Dashboard matplotlib a nuevos topics.

---

## Fase 5 — GPP

FL assignment con DEM (SRTM) + NFZ GeoJSON + márgenes vs `quality_flag`. RRT\* + OMPL en SE(2) con Dubins y PolyCARP como collision checker; path en `/gpp/global_path`. Benchmark 50 runs. Takeoff/Landing managers básicos (VR, glide, go-around).

---

## Fase 6 — Replanificador local

Coste explícito, triggers (quality, polycarp, daidalus, desviación), políticas por trigger, mapa aterrizaje emergencia simplificado, tests de prioridad y filtrado por vehicle model.

---

## Fase 7 — Generación trayectoria

Dubins 3D / suavizado, chequeo vs envelope antes de publicar, `/trajectory/setpoints` (2 Hz nominal, 10 Hz en alerta), tests curvatura y climb.

---

## Fase 8 — ACAS Xu

Proceso separado alta prioridad (`chrt`), solo ownship + tráfico, override a FC con latencia &lt; 100 ms en test de integración.

---

## Fase 9 — E2E + V&V

Launch único, cuatro escenarios (`scenario_*.sh`), matriz REQUIREMENTS.md, rosbags, demo grabable.

---

## Referencias cruzadas

- Stack **Flightmind** (DAIDALUS ya enlazado + planner): repositorio `px4-flightmind` (fuera de este workspace).
- Este workspace (`upnext_uas_ws`) acoge la **descomposición modular** del roadmap anterior.
