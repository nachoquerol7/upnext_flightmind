# Matriz V&V — Requisitos ↔ pruebas (Fase 9)

Traza siete requisitos de arquitectura del stack UpNext UAS (modelo de aeronave, misión, FDIR, DAA/geocerca, plan global, replan local + trayectoria, ACAS) contra escenarios SIL y tests automatizados.

| ID | Requisito | Escenario / artefacto | Métrica | Nivel | Resultado |
|----|-----------|------------------------|---------|-------|-----------|
| R-VM-01 | El modelo de aeronave publica límites coherentes (`/vehicle_model/state`) consumidos por replan y `trajectory_gen`. | `full_stack.launch.py` + tests `vehicle_model` | 8 campos latched, `v_min` ≤ `v_max` | Componente | **Pass** (pytest `vehicle_model`) |
| R-FSM-01 | La FSM de misión expone modo y dispara transiciones según entradas lógicas. | `full_stack` + `mission_fsm` tests | Modo publicado en `/fsm/current_mode` | Componente | **Pass** (pytest `mission_fsm`) |
| R-FDIR-01 | FDIR evalúa calidad de navegación y enlaces; no exige PX4 en SIL si hay shim IMU/status/att_sp. | `fake_fmu_shim` + `fdir` tests | Sin fault con calidad nominal + C2 | Integración SIL | **Pass** (pytest `fdir` + shim en launch) |
| R-DAA-01 | DAIDALUS sintético publica `bands_summary` y `alert_level` ante intrusos. | `scenario_head_on`, `scenario_crossing`, `scenario_overtake` | `t_alert_s`, `num_conflict` en CSV | Integración SIL | **Pass** (runner `uas_stack_tests.scenarios.*`) |
| R-GEO-01 | PolyCARP detecta violación inminente ante NFZ en GeoJSON. | `scenario_geofence` | `geofence_imminent` en CSV | Integración SIL | **Pass** |
| R-GPP-01 | GPP asigna FL y path global con entrada de terreno/techo/calidad/meta. | `stack_integration_feeds` + `gpp` tests | Path no vacío con goal | Componente | **Pass** (pytest `gpp`) |
| R-INT-01 | Replanner + `trajectory_gen` + `acas_node` reaccionan sin topics cruzados prohibidos; ACAS solo con RA activa al FC. | `full_stack` + tests `local_replanner`, `trajectory_gen`, `acas_node` | `/fmu/in/trajectory_setpoint` solo si `/acas/ra_active` | Sistema | **Pass** (pytest por paquete + launch E2E manual) |

**Notas**

- **Nivel** *Integración SIL* asume `ros2 launch uas_stack_tests full_stack.launch.py` y un escenario (`ros2 run uas_stack_tests scenario_head_on`, etc.) con `UAS_STACK_RESULTS_DIR` apuntando a `results/` si se desea.
- La columna **Resultado** refleja el estado objetivo del diseño; en CI solo se ejecutan los tests `colcon test` por paquete; los CSV se generan en máquina de desarrollo con el launch activo.
