# Fase 1 — M3 integridad estática del grafo FSM

## Tests implementados

| ID | Descripción breve |
|----|-------------------|
| TC-INT-001 | YAML raíz es mapping con `fsm` |
| TC-INT-002 | Extremos de transición son estados declarados |
| TC-INT-003 | `initial_state` existe en `fsm.states` |
| TC-INT-004 | Átomos en `when` son builtins o entradas por defecto |
| TC-INT-005 | Átomos en `entry_guards` conocidos |
| TC-INT-006 | Cada estado es `initial` o aparece como `to` en alguna transición |
| TC-INT-007 | Cobertura de transiciones (placeholder, skip hasta M1+M2) |
| TC-INT-008 | Tras arranque, `/fsm/current_mode` recibe al menos un mensaje en &lt; 5 s |

## Tests que pasan

- TC-INT-001 … TC-INT-006, TC-INT-008.

## Tests omitidos

- TC-INT-007: `pytest.mark.skip` — ejecutar cuando M1+M2 estén completos (cobertura frente a YAML).

## Tests XFAIL-ARCH

- Ninguno en esta fase.

## Decisiones de implementación

- TC-INT-008 importa `Node` desde `rclpy.node` (corrección NameError).
- TC-INT-008 gestiona `rclpy.init`/`shutdown` localmente para no depender del fixture `ros_context` y evitar interferencias con el executor dedicado del test.
