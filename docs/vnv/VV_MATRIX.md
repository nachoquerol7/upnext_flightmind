# V&V Traceability Matrix

Matriz SR → TC para cierre MBSE (SR-VV-01). Los estados reflejan la suite `mission_fsm` y el índice XFAIL.

| SR ID | Descripción | TC IDs | Módulo | Estado |
|-------|-------------|--------|--------|--------|
| SR-FSM-01 | FSM PREFLIGHT→AUTOTAXI con preflight_ok | TC-FSM-001 | M1 | PASS |
| SR-FSM-02 | FSM AUTOTAXI→TAKEOFF con taxi_clear | TC-FSM-002 | M1 | PASS |
| SR-FSM-03 | FSM TAKEOFF→CRUISE con takeoff_complete | TC-FSM-003 | M1 | PASS |
| SR-FSM-04 | FSM CRUISE→EVENT ante quality_degraded / DAIDALUS | TC-FSM-004 | M1 | PASS |
| SR-FSM-05 | FSM CRUISE→RTB con rtb_command | TC-FSM-005 | M1 | PASS |
| SR-FSM-06 | FSM CRUISE→LANDING con land_command | TC-FSM-006 | M1 | PASS |
| SR-FSM-07 | FSM EVENT→CRUISE con event_cleared | TC-FSM-007 | M1 | PASS |
| SR-FSM-08 | FSM CRUISE→ABORT con abort_command o fdir_emergency | TC-FSM-008 | M1 | PASS |
| SR-FSM-09 | Orden de evaluación abort vs EVENT (TC-FSM-019) | TC-FSM-019 | M1 | PASS |
| SR-FSM-10 | Modo ABORT y transiciones subsiguientes | TC-FSM-020 | M1 | PASS |
| SR-DAI-01 | Nivel DAIDALUS FAR reflejado en FSM/topic | TC-DAI-001 | M5 | PASS |
| SR-DAI-02 | Nivel DAIDALUS MID | TC-DAI-002 | M5 | PASS |
| SR-DAI-03 | Nivel DAIDALUS NEAR y escalado FSM | TC-DAI-003 | M5 | PASS |
| SR-DAI-04 | Clear alert (0) | TC-DAI-004 | M5 | XFAIL-ARCH-1.1 |
| SR-DAI-05 | Nivel RECOVERY / mapeo explícito | TC-DAI-005 | M5 | XFAIL-ARCH-DAI-RECOVERY |
| SR-DAI-06 | Timeout feed DAIDALUS | TC-DAI-008 | M5 | XFAIL-ARCH-DAI-FEED |
| SR-DAI-07 | Advisory / integración validación | TC-DAI-009 | M5 | XFAIL-ARCH-DAI-ADV |
| SR-FDIR-01 | Emergency flag publicado | TC-FDIR-001 | M6 | PASS |
| SR-FDIR-02 | Reset emergency | TC-FDIR-002 | M6 | PASS |
| SR-FDIR-03 | active_fault no vacío | TC-FDIR-009 | M6 | PASS |
| SR-FDIR-04 | Severidad tabulada en cascada | TC-FAULT-012 | M6 | XFAIL-ARCH-FDIR-SEV |
| SR-FDIR-05 | Watchdog temporal / supervisión | TC-FDIR-007 | M6 | XFAIL-ARCH-1.7 |
| SR-FDIR-06 | Estado STALE/DEAD en integración | TC-FDIR-008 | M6 | XFAIL-ARCH-1.7 |
| SR-E2E-01 | Misión nominal hasta CRUISE | TC-E2E-001 | M9 | PASS |
| SR-E2E-02 | Memoria / leak misión | TC-E2E-007 | M9 | XFAIL-ARCH-1.10 |
| SR-E2E-03 | Black-box logging | TC-E2E-009 | M9 | XFAIL-ARCH-1.10 |
| SR-E2E-04 | Replay catálogo | TC-E2E-010 | M9 | XFAIL-ARCH-1.10 |
| SR-E2E-05 | Trayectoria E2E con calidad | TC-E2E-002 | M9 | PASS |
| SR-E2E-06 | Evento intruso en cadena nominal | TC-E2E-003 | M9 | PASS |
| SR-E2E-07 | Reanudación tras EVENT | TC-E2E-004 | M9 | PASS |
| SR-E2E-08 | Integridad trayectoria global | TC-E2E-005 | M9 | PASS |
| SR-E2E-09 | Fault injection coordinada | TC-FAULT-001 | M9/M10 | XFAIL-ARCH-1.9 |
| SR-E2E-10 | Persistencia waypoint interrupción | TC-NAV-009 | M9 | XFAIL-ARCH-1.9 |
| SR-PERF-01 | Latencia transición FSM (P99) | TC-PERF-001 | M11 | PASS |
| SR-PERF-02 | Throughput evaluación transiciones | TC-PERF-002 | M11 | PASS |
| SR-PERF-03 | WCET ruta crítica CRUISE→ABORT | TC-PERF-003 | M11 | PASS |
| SR-PERF-04 | Jitter σ transiciones | TC-PERF-004 | M11 | PASS |
| SR-PERF-05 | Carga concurrente step() | TC-PERF-005 | M11 | PASS |
| SR-PERF-06 | Footprint RAM instancia FSM | TC-PERF-006 | M11 | PASS |
| SR-PERF-07 | Degradación con logging | TC-PERF-007 | M11 | PASS |
| SR-PERF-08 | Parse YAML variantes plataforma | TC-PERF-008 | M11 | PASS |

**Nota:** Los SR se etiquetan de forma estable para trazabilidad; los TC con XFAIL enlazan con `src/mission_fsm/docs/vnv/XFAIL_INDEX.md` y gaps GPP en `src/gpp/docs/vnv/XFAIL_INDEX_GPP.md` cuando aplica.
