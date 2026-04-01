# Índice XFAIL — SIL FlightMind

Casos marcados como **XFAIL** en el testbench refieren **gaps arquitecturales** documentados en el plan V&V (no fallos de implementación aislados).

| Referencia | Alcance |
|------------|---------|
| ARCH-1.2 | Timeouts de supervisión / morada FSM — requiere orquestación externa o extensión del nodo FSM. |
| ARCH-1.7 | Supervisión temporal adicional — ver plan maestro UAS_SIL_VnV_Plan_v2. |

Los TCs bajo prefijo `TC-TO-*` (M2) se asocian a estos gaps en `js/tc_definitions.js`.
