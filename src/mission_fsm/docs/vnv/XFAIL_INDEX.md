# Índice XFAIL-ARCH (gaps de arquitectura)

## ARCH-1.1 — Histéresis y fast-path de alertas
**Estado:** ABIERTO
**Tests bloqueados:** TC-FSM-023, TC-DAI-004
**Descripción:** El stack no implementa histéresis temporal ni fast-path diferenciado para alerta DAIDALUS NEAR.
**Impacto:** Oscilaciones y latencia de reacción no controlada en escenarios de alerta.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.2 — Timeouts de morada FSM
**Estado:** ABIERTO
**Tests bloqueados:** TC-TO-001, TC-TO-002, TC-TO-003, TC-TO-004, TC-TO-005, TC-TO-010
**Auditoría M2 (2026-04):** Sin falsos XFAIL; el YAML no define `max_duration_sec` y `mission_fsm_node` no implementa temporizador de morada. La suite M2 incluye tests `test_m2_audit_*` que pasan y documentan el vacío arquitectónico.
**Descripción:** Sin max_duration_sec operativo por estado ni watchdog temporal de misión.
**Impacto:** Posibilidad de quedar indefinidamente en estados sin progreso.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.3 — Subestados EVENT
**Estado:** ABIERTO
**Tests bloqueados:** TC-FSM-024
**Descripción:** `/fsm/current_mode` no expone subestado operativo dentro de EVENT.
**Impacto:** Menor observabilidad para operación y V&V avanzada.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.4 — Transición CRUISE→ABORT por fdir_emergency
**Estado:** CERRADO
**Fecha cierre:** 2026-04-01
**Tests bloqueados:** —
**Descripción:** La transición `cruise_to_abort` solo exigía `abort_command`; faltaba `fdir_emergency` como disparador directo desde CRUISE.
**Cierre:** `mission_fsm.yaml`: `when: any: [abort_command, fdir_emergency]` en la transición CRUISE→ABORT.
**Impacto:** —
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.6 — Validación geofence pre-Nav2
**Estado:** ABIERTO
**Tests bloqueados:** TC-NAV-006, TC-FAULT-005
**Descripción:** No hay validador que rechace waypoints fuera de geofence antes de llamar a Nav2.
**Impacto:** Planificación de rutas potencialmente inválidas para plataforma aérea.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.7 — Supervisión externa (watchdog + enlaces)
**Estado:** ABIERTO
**Tests bloqueados:** TC-TO-006, TC-TO-007, TC-TO-008, TC-TO-009, TC-FDIR-007, TC-FDIR-008, TC-FDIR-016, TC-MW-001, TC-FAULT-008
**Auditoría M2 (2026-04):** TC-TO-006..009 permanecen XFAIL legítimos (sin integración temporal GCS/C2/batería/geofence en el nodo).
**Descripción:** No existe nodo watchdog integrado ni monitor temporal de GCS/C2/batería/geofence en mission_fsm.
**Impacto:** Degradación de seguridad ante caída de nodos o pérdida de enlaces críticos.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.8 — Monitor de localización
**Estado:** ABIERTO
**Tests bloqueados:** TC-LOC-003, TC-LOC-004, TC-LOC-012
**Descripción:** Ausencia de monitor para timeout de odometría y discontinuidad de pose.
**Impacto:** Fallos de localización no detectados de forma explícita.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.9 — Persistencia de waypoint de interrupción
**Estado:** ABIERTO
**Tests bloqueados:** TC-NAV-009, TC-FAULT-001
**Descripción:** El gestor de misión no persiste waypoint actual para reanudación tras interrupción.
**Impacto:** Reanudación no determinista tras EVENT/ABORT en misiones largas.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-1.10 — Black box logging / replay
**Estado:** ABIERTO
**Tests bloqueados:** TC-E2E-009, TC-E2E-010
**Descripción:** No existe subsistema de black-box con registro persistente y catálogo de replay para misiones.
**Impacto:** Menor trazabilidad post-vuelo y diagnóstico limitado en incidentes.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-DAI-RECOVERY — Mapeo nivel RECOVERY
**Estado:** ABIERTO
**Tests bloqueados:** TC-DAI-005
**Descripción:** Nivel DAIDALUS RECOVERY (4) no tiene mapeo explícito en FSM.
**Impacto:** Comportamiento ambiguo ante recuperación/conflicto severo.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-DAI-FEED — Timeout de feed DAIDALUS
**Estado:** ABIERTO
**Tests bloqueados:** TC-DAI-008
**Descripción:** No existe timeout de ausencia de topic DAIDALUS.
**Impacto:** Pérdida de feed no escalada automáticamente.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-DAI-ADV — Integración/validación advisory
**Estado:** ABIERTO
**Tests bloqueados:** TC-DAI-009, TC-DAI-010, TC-DAI-012
**Descripción:** Falta consumo operativo y validación de advisory (incluyendo geofence/frescura).
**Impacto:** Advisory recibido no se traduce en acciones seguras y verificables.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-NAV — Adaptador Nav2 para UAS
**Estado:** ABIERTO
**Tests bloqueados:** TC-NAV-004, TC-NAV-005
**Descripción:** No hay ActionServer `/navigate_to_pose` en mock/adapter ni adaptación de recovery behavior para plataforma aérea.
**Impacto:** Integración Nav2 incompleta para SIL de UAS.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-UTM — Interfaz UTM dinámica
**Estado:** ABIERTO
**Tests bloqueados:** TC-NAV-011
**Descripción:** Falta interfaz para restricciones UTM dinámicas antes/durante planificación.
**Impacto:** No se pueden validar restricciones de espacio aéreo en tiempo de misión.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-FDIR-SEV — Tabla de severidad de fallos FDIR
**Estado:** ABIERTO
**Tests bloqueados:** TC-FAULT-012
**Descripción:** No hay tabla/versionado de severidad para cascada de fallos en FDIR.
**Impacto:** Escalado de emergencia no determinista para fallos múltiples simultáneos.
**Responsable:** —
**Fecha objetivo:** —

## ARCH-BRIDGE — Topics de subsistema hacia /fsm/in/*
**Estado:** ABIERTO
**Tests bloqueados:** (indirecto en múltiples suites)
**Descripción:** El puente real de topics de subsistema a entradas de FSM no está integrado; se duplica en mocks SIL.
**Impacto:** Riesgo de divergencia entre SIL y despliegue integrado.
**Responsable:** —
**Fecha objetivo:** —
