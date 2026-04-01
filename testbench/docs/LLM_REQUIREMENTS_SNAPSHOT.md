# FlightMind / UpNext — snapshot para certificación (LLM Analyst)

Documento **resumen** alineado con matrices V&V del repo (`docs/vnv/VV_MATRIX.md`, `src/uas_stack_tests/docs/VV_MATRIX.md`) y con la FSM operativa en `mission_fsm/config/mission_fsm.yaml`. Úsalo para relacionar fallos de TC con IDs de requisito.

---

## Parámetros ROS nominales (`mission_fsm_node`)

| Parámetro | Valor típico | Rol |
|-----------|--------------|-----|
| `tick_hz` | 20 Hz | Periodo del reloj de paso FSM en el nodo |
| `quality_flag_threshold` | 0.5 | Umbral calidad localización |
| `hysteresis_ticks_on` | 3 | Ticks bajo umbral antes de `quality_degraded` (ARCH-1.1) |
| `hysteresis_ticks_off` | 5 | Ticks sobre umbral+margen antes de recuperación |
| `hysteresis_margin` | 0.05 | Banda muerta alrededor del umbral |
| `daidalus_alert_amber` | 1 | Nivel mínimo “ámbar” DAIDALUS |
| `daidalus_escalate_ticks` | 2 | Ticks en banda MID antes de `daidalus_escalated` |
| `daidalus_feed_timeout_sec` | 2.0 s | Pérdida de feed DAIDALUS → EVENT (CRUISE+) |
| `gcs_heartbeat_timeout_sec` | 2.0 s | Sin `/gcs_heartbeat` → `gcs_lost` |
| `c2_link_loss_sec` | 2.0 s | Enlace C2 falso sostenido → `c2_lost` |
| `battery_low_threshold` | 0.15 | Fracción batería bajo umbral |
| `battery_low_sustain_sec` | 2.0 s | Sostenimiento bajo umbral → `battery_low` supervisado |
| `geofence_breach_sustain_sec` | 0.5 s | Sostenimiento violación → `geofence_violation` / `geofence_breach` |
| `max_duration_sec` (estado) | 5.0 s | PREFLIGHT, AUTOTAXI, TAKEOFF, CRUISE, EVENT — morada máxima antes de `state_dwell_timeout` |

---

## FSM — requisitos funcionales clave (SR ↔ TC)

| ID | Descripción | TC representativo | Criterio de éxito breve |
|----|-------------|-------------------|-------------------------|
| SR-FSM-01 | PREFLIGHT→AUTOTAXI con `preflight_ok` | TC-FSM-001 | Modo AUTOTAXI tras comando |
| SR-FSM-02 | AUTOTAXI→TAKEOFF con `taxi_clear` | TC-FSM-002 | TAKEOFF al despeje taxi |
| SR-FSM-03 | TAKEOFF→CRUISE con `takeoff_complete` | TC-FSM-003 | CRUISE nominal |
| SR-FSM-04 | CRUISE→EVENT ante calidad degradada / escalado DAIDALUS | TC-FSM-004 | EVENT con trigger `to_event` o near/recovery |
| SR-FSM-05 | CRUISE→RTB con `rtb_command` | TC-FSM-005 | RTB |
| SR-FSM-06 | CRUISE→LANDING con `land_command` | TC-FSM-006 | LANDING |
| SR-FSM-07 | EVENT→CRUISE con `event_cleared` | TC-FSM-007 | Retorno CRUISE |
| SR-FSM-08 | CRUISE→ABORT ante `abort_command`, `fdir_emergency`, **`battery_low`**, **`geofence_breach`** | TC-FSM-008, TC-ATOM-001/004 | ABORT (puede encadenar RTB por `abort_to_rtb`) |
| SR-FSM-09 | Prioridad abort vs EVENT | TC-FSM-019 | `cruise_to_abort` gana cuando aplica |
| SR-FSM-10 | ABORT y transiciones siguientes | TC-FSM-020 | Cadena ABORT→RTB observable |
| SR-FSM-MORA | Morada > `max_duration_sec` en estado | TC-TO-001…005, TC-TO-010 | `state_dwell_timeout` dispara transición de fallo |

**Orden YAML:** en cada estado, la **primera** transición cuyo `when` cumple gana (abort temprano, dwell, etc.).

---

## DAA / DAIDALUS — requisitos clave

| ID | Descripción | TC | Notas |
|----|-------------|-----|-------|
| SR-DAI-01..03 | Niveles FAR / MID / NEAR reflejados en FSM | TC-DAI-001..003 | Entrada vía `/fsm/in/daidalus_alert` o adaptador |
| SR-DAI-04 | Clear (0) sin oscilación indebida | TC-DAI-004 | Puede depender de histéresis / fast-path |
| SR-DAI-05 | RECOVERY (≥4) | TC-DAI-005 | Trigger `to_recovery` |
| SR-DAI-06 | Timeout feed | TC-DAI-008 | `daidalus_feed_lost` |
| R-DAA-01 | `bands_summary` / `alert_level` en SIL | escenarios `uas_stack_tests` | Métricas CSV |

---

## GPP — requisitos clave

| ID | Descripción | TC / artefacto | Criterio |
|----|-------------|----------------|----------|
| R-GPP-01 | Asignación FL + path global con meta y restricciones | pytest `gpp`, `stack_integration_feeds` | Path no vacío hacia goal |
| SR-GPP (catálogo L1) | Informed-RRT*, Dubins, geofences | PDF L1-GPP + VnV GPP | Cobertura en tests por módulo GPP |

---

## FDIR / supervisión

- Tabla severidad: `src/fdir/config/fdir_severity.yaml` (acciones ABORT/RTB/DEGRADE).
- Heartbeats críticos: `/fsm/heartbeat`, `/daidalus/heartbeat`, `/navigation/heartbeat`, `/acas/heartbeat` (watchdog FDIR).

---

## Mensajes ROS (`flightmind_msgs`)

`FSMState`, `NavigationState`, `TrafficReport`, `TrafficIntruder`, `DaidalusBands`, `DaidalusAlert`, `ACASAdvisory`, `GeofenceStatus`, `TrajectorySetpoint`, `VehicleModelState`.

---

## Instrucciones para el modelo (certificación)

1. Cuando el usuario pegue resultado de un **TC** o transición FSM, cita **SR-xxx** o **R-xxx** si aplica según tablas anteriores.
2. Si el tiempo en estado supera **5 s** en PREFLIGHT/AUTOTAXI/TAKEOFF/CRUISE/EVENT sin progresión válida, señala incumplimiento de **morada** (SR-FSM-MORA / parámetros tabla).
3. Si la calidad cruza el umbral sin respetar **3 ticks** bajo umbral, señala posible problema de **histéresis** (ARCH-1.1).
4. **Batería baja** supervisada o átomo `battery_low` en CRUISE debe producir **`cruise_to_abort`**, no RTB directo.
5. **Geofence** activo en CRUISE debe producir **`cruise_to_abort`** (mismo trigger).
6. Responde en **español**, máximo 3–4 frases, tono auditor V&V.
