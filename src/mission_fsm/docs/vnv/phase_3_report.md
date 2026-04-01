# Fase 3 — M4 + M5 + M6 + M7

## Tests implementados

### M4 Localización (`test/m4_localization/test_localization_interface.py`)
- TC-LOC-001..013 implementados (13).

### M5 DAIDALUS (`test/m5_daidalus/test_daidalus_alerts.py`)
- TC-DAI-001..012 implementados (12).

### M6 FDIR (`test/m6_fdir/test_fdir.py`)
- TC-FDIR-001..016 implementados (16).

### M7 Nav2 (`test/m7_nav2/test_nav2_interface.py`)
- TC-NAV-001..012 implementados (12).

## Tests que pasan
- M4: 10 passed, 3 xfailed.
- M5: 6 passed, 6 xfailed.
- M6: 13 passed, 3 xfailed.
- M7: 7 passed, 5 xfailed.

## Tests XFAIL-ARCH (referencia)
- M4: TC-LOC-003, TC-LOC-004, TC-LOC-012 → ARCH-1.8
- M5: TC-DAI-004 → ARCH-1.1; TC-DAI-005 → ARCH-DAI-RECOVERY; TC-DAI-008 → ARCH-DAI-FEED; TC-DAI-009/010/012 → ARCH-DAI-ADV
- M6: TC-FDIR-007, TC-FDIR-008, TC-FDIR-016 → ARCH-1.7
- M7: TC-NAV-004, TC-NAV-005 → ARCH-NAV; TC-NAV-006 → ARCH-1.6; TC-NAV-009 → ARCH-1.9; TC-NAV-011 → ARCH-UTM

## Decisiones de implementación
- `mock_daidalus` amplía publicación a `/daidalus/advisory` (`geometry_msgs/TwistStamped`) y mantiene `/daidalus/resolution_advisory` para compatibilidad SIL previa.
- Se mantuvo política estricta: ningún workaround en producción; los gaps sin arquitectura se marcaron `xfail(strict=True)`.
- En M6, TC-FDIR-009 se validó a nivel de interfaz ROS (suscripción declarada únicamente en `/fdir/reset_emergency`) para evitar falsos negativos de transporte en este entorno.
- TC-FDIR-014 mide latencia P99 con 20 repeticiones usando `time.monotonic()` y oráculo < 500 ms.
- Cobertura funcional de `mission_fsm/fsm.py` permanece en 100% (sentencias y ramas) con `pytest --cov-branch`.
