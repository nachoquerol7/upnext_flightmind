# Fase 4 — M8 ROS2 Middleware

## Tests implementados

- `test/m8_middleware/test_ros2_middleware.py` con TC-MW-001..010.
- Cobertura de tópicos críticos: `/fsm/state` (FSMState), legacy `/fsm/current_mode`, `/fsm/active_trigger`, QoS y parámetros.

## Tests que pasan

- 7 passed:
  - TC-MW-002, TC-MW-004, TC-MW-005, TC-MW-006, TC-MW-007, TC-MW-008, TC-MW-009.

## Tests XFAIL-ARCH / XFAIL

- TC-MW-001 → `XFAIL-ARCH-1.7`: `/watchdog/status` no implementado.
- TC-MW-003 → XFAIL infraestructura: captura de warning QoS incompatible no estable vía callback/log en este entorno.
- TC-MW-010 → XFAIL infraestructura: aislamiento multi-domain no estable en harness single-process actual.

## Decisiones de implementación

- Se validó `/fsm/state` como contrato principal y se comprobó convivencia con los tópicos legacy.
- TC-MW-007 usa `ros2 param get` contra `mission_fsm_node` en proceso real para comprobar coincidencia con YAML.
- TC-MW-009 mide tiempo de arranque hasta primer `FSMState` con `time.monotonic()` y umbral 15 s.
