# Fase 2 — M1 transiciones + M2 timeouts (ROS 2 SIL)

## Tests implementados

### M1 (`test/m1_fsm_transitions/test_fsm_transitions.py`)

| ID | Resumen |
|----|---------|
| TC-FSM-001 … 018 | Transiciones YAML vía `/fsm/in/*`, oráculo sobre `/fsm/current_mode` y lista `cap.triggers` |
| TC-FSM-019 | Orden CRUISE: `abort_command` gana sobre vía EVENT (`cruise_to_abort`, sin `to_event`) |
| TC-FSM-020 | `rtb_command` + `land_command` → `cruise_to_rtb` (primera coincidencia YAML) |
| TC-FSM-021 | Sin `preflight_ok` permanece PREFLIGHT |
| TC-FSM-022 | AUTOTAXI sin `taxi_clear` no avanza |
| TC-FSM-023 | Parámetro de histéresis de calidad en el nodo (xfail) |
| TC-FSM-024 | Subestados de EVENT en `current_mode` (xfail) |

### M2 (`test/m2_fsm_timeouts/test_fsm_timeouts.py`)

| ID | Resumen |
|----|---------|
| TC-TO-001 … TC-TO-005, TC-TO-010 | Timeouts de morada / misión (xfail ARCH-1.2) |
| TC-TO-006 … TC-TO-009 | GCS, C2, batería, geofence (xfail ARCH-1.7) |

## Tests que pasan

- M1: TC-FSM-001 … TC-FSM-022 (22 tests).
- Resto del paquete (transiciones puras Python, Fase 0, M3 según fase anterior).

## Tests XFAIL-ARCH (strict=True)

| Gap | Tests |
|-----|--------|
| ARCH-1.1 | TC-FSM-023 |
| ARCH-1.2 | TC-TO-001 … TC-TO-005, TC-TO-010 |
| ARCH-1.3 | TC-FSM-024 |
| ARCH-1.7 | TC-TO-006 … TC-TO-009 |

## Decisiones de implementación

- **`mission_fsm_sil_harness`**: `MissionFsmNode` + `FsmInputInjector` + `_FsmModeCapture` con historial `triggers` (el nodo publica trigger vacío en ticks sin transición).
- **`spin_until`**: el fixture exponía mal el argumento `timeout_sec`; se corrigió para esperas hasta 5 s tras estímulos (varios nodos en `MultiThreadedExecutor`).
- **SIL puente calidad/DAIDALUS**: `mock_fastlio2` y `mock_daidalus` publican también en `/fsm/in/*` con comentarios `GAP-ARCH-BRIDGE` (el nodo de misión no se suscribe a topics de subsistema).
- **`fsm_input_injector.py`**: publica todos los booleanos de `_BOOL_TOPICS` más `quality_flag` y `daidalus_alert` alineados con `mission_fsm_node`.
- **M2**: oráculos exigen transiciones que el YAML/nodo aún no implementan; todos marcados xfail sin tocar código de producción.
