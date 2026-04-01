# Cobertura L1 (flightmind-design) ↔ implementación `upnext_uas_ws`

**Fuente L1:** `/home/ignacio-querol/flightmind-design/L0/L1 */SUB_*_Requirements.pdf` (texto extraído con `pdftotext`, abril 2026).  
**Conclusión global:** **ningún subsistema L1 está al 100 %** frente a su PDF; varios están **parcialmente** cubiertos por SIL, nodos ROS y tests `colcon`. **L1-LPP** no tiene PDF en el directorio indicado.

| Subsistema | PDF L1 | IDs (aprox.) | Paquete(s) / artefacto principal | Cobertura en SIL | Brechas típicas |
|------------|--------|----------------|-----------------------------------|------------------|-----------------|
| **ACAS** | `L1 - ACAS/SUB_ACAS_Requirements.pdf` | ACAS-001 … ~023 | `acas_node`, `third_party/acas_xu_nnets` | **Parcial** | Red Xu, softmax, subs alert_level; no todo DO-386 / integración FC completa |
| **AIR** | `L1- AIR/SUB_AIR_Requirements.pdf` | AIR-001 … ~023 | `upnext_airspace`, `polycarp_node`, topics geocerca en FSM | **Parcial** | Validación GeoJSON/NFZ completa, algunos TC-NAV xfail |
| **C2** | `L1- C2/SUB_C2_Requirements.pdf` | C2-001 … C2-014 | `fdir` (`c2_monitor`), `mission_fsm_node` (`/c2_link_status`) | **Parcial** | PDF marca varios PENDIENTE/XFAIL; no gateway MAVLink 2 completo en este repo |
| **DAA** | `L1 - DAA/SUB_DAA_Requirements.pdf` | DAA-001 … ~065 | `daidalus_node`, `upnext_icarous_daa`, escenarios `uas_stack_tests` | **Parcial** | Muchos requisitos DO-365/ED-269; logging DAA-066, advisory completo |
| **FDIR** | `L1 - FDIR/SUB_FDIR_Requirements.pdf` | FDIR-001 … ~036 | `fdir`, `fdir_severity.yaml`, `watchdog_node` | **Parcial** | Watchdog TCs xfail según índice; severidad cascada TC-FAULT-012 xfail |
| **FSM** | `L1 - FSM/SUB_FSM_Requirements.pdf` + ICD | FSM-001 … ~084 | `mission_fsm`, `mission_fsm.yaml`, testbench M1–M13 | **Parcial–alto** | Subestados EVENT (ARCH-1.3), requisitos documentales/to_dict si no en código |
| **GCS** | `L1 - GCS/SUB_GCS_Requirements.pdf` | GCS-001 … ~026 | `mission_fsm_node` (`/gcs_heartbeat`) | **Bajo** | No hay nodo GCS completo; solo consumo heartbeat en FSM |
| **GPP** | `L1 - GPP/SUB_GPP_Requirements.pdf` | GPP-001 … ~039 | `gpp`, tests pytest por módulo | **Parcial–alto** | Gaps en `XFAIL_INDEX_GPP.md`; EU OPS urbano / SORA no todo automatizado |
| **LPP** | `L1 - LPP/` | **(vacío)** | — | **N/A** | Añadir PDF o eliminar carpeta; no hay paquete `lpp` / local planner dedicado en `src/` |
| **NAV** | `L1 - NAV/SUB_NAV_Requirements.pdf` | NAV-001 … ~026 | `navigation_bridge`, mocks FastLIO en tests | **Parcial** | Nav2 adapter, monitores LOC xfail (ARCH-1.8) |
| **REPL** | `L1 - REPL/SUB_REPL_Requirements.pdf` | REPL-001 … ~020 | `local_replanner` | **Bajo–parcial** | RRT* local / coste DAA en gran parte stub o simplificado |
| **TEST** | `L1 - TEST/SUB_TEST_Requirements.pdf` | TEST-001 … ~032 | `testbench`, `.github/workflows/ci.yml`, `mission_fsm` pytest | **Parcial** | CI no ejecuta todos los paquetes; DO-178C cobertura objetivo no demostrada al 100 % |
| **TRAJ** | `L1 - TRAJ/SUB_TRAJ_Requirements.pdf` | TRAJ-001 … ~020 | `trajectory_gen` | **Parcial** | 50 Hz / misión completa implementados de forma básica; no todo TRAJ-011+ |
| **VM** | `L1 - VM/SUB_VM_Requirements.pdf` | VM-001 … ~025 | `vehicle_model` | **Parcial** | Solo subconjunto VM en nodo actual vs 25 IDs L1 |

## Criterio de “implementado”

- **Sí / alto:** lógica principal en nodo ROS + tests que ejercitan el requisito o SR derivado en `docs/vnv/VV_MATRIX.md`.
- **Parcial:** parte de la cadena existe (topic, FSM, mock); faltan casos, HIL o requisitos SHOULD/MAY del PDF.
- **Bajo / gap:** requisito no enlazado a código en este workspace o explícitamente **XFAIL** / **PENDIENTE** en el propio PDF L1.

## Acciones recomendadas (prioridad)

1. **LPP:** Publicar `SUB_LPP_Requirements.pdf` o retirar carpeta vacía; decidir si LPP vive en otro repo (px4-flightmind planner).
2. **GCS:** Si L1 exige operador/UI, añadir nodo shim o documentar que solo se valida **supervisión en FSM**.
3. **Matrices:** Mantener `VV_MATRIX.md` y `testbench/docs/LLM_REQUIREMENTS_SNAPSHOT.md` alineados con cambios YAML (p. ej. `cruise_to_abort` con batería/geocerca).
4. **Auditoría por ID:** Para cierre formal, generar CSV Req-ID → archivo/test → PASS/PARTIAL/GAP desde los PDF (columnas “Verificación” ya orientan en varios subsistemas).

## Regenerar extracción PDF (local)

```bash
mkdir -p /tmp/l1_extract
for pdf in /home/ignacio-querol/flightmind-design/L0/**/SUB_*_Requirements.pdf; do
  pdftotext "$pdf" "/tmp/l1_extract/$(basename "$pdf" .pdf).txt"
done
```

---

*Documento generado para trazabilidad; no sustituye la aprobación de diseño ni el análisis de seguridad (DAL) del PDF original.*
