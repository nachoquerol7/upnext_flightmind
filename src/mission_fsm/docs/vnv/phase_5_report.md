# Fase 5 — M9 nominal + M10 fault injection

## Tests implementados

### M9 (`test/m9_e2e_nominal/test_e2e_nominal.py`)
- TC-E2E-001 .. TC-E2E-010 implementados.
- Soporte de configuraciones por plataforma:
  - `config/mission_fsm_vtol.yaml`
  - `config/mission_fsm_heli.yaml`
  - `config/mission_fsm_male.yaml`

### M10 (`test/m10_e2e_faults/test_e2e_faults.py`)
- TC-FAULT-001 .. TC-FAULT-012 implementados.

## Tests que pasan

- M9: 8 passed, 2 xfailed.
- M10: 8 passed, 4 xfailed.

## Tests XFAIL-ARCH (con referencia)

- M9
  - TC-E2E-009, TC-E2E-010 → ARCH-1.10
- M10
  - TC-FAULT-001 → ARCH-1.9
  - TC-FAULT-005 → ARCH-1.6
  - TC-FAULT-008 → ARCH-1.7
  - TC-FAULT-012 → ARCH-FDIR-SEV

## Decisiones de implementación tomadas

- Los tests E2E consumen `FSMState` desde `/fsm/state`; no dependen de tópicos legacy.
- TC-E2E-007 usa `psutil` para medir RSS del proceso y aplica umbral de crecimiento de 10MB entre misión 1 y 5.
- Las pruebas de black box y persistencia de waypoint se dejaron en `xfail(strict=True)` para no introducir workarounds arquitecturales.
- Se agregó saneamiento de fixture en `conftest.py` para evitar contaminación por procesos/estado latcheado entre pruebas.
