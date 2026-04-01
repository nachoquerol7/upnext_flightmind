# Primer vuelo simulado — PX4 SITL + stack FlightMind (informe)

**Timestamp:** 2026-04-01T16:48:25+02:00 (fin de la secuencia de smoke documentada)

## Resumen

Se ejecutó un ciclo completo **SITL + Micro XRCE-DDS Agent + `mission_fsm` + `acas_node`**, con comprobación manual de transiciones del FSM vía `/fsm/state`. PX4 se arrancó en modo **SIH** (simulador en proceso) por incompatibilidades del autostart original con el entorno (véase ajustes).

**Testbench / rosbridge (terminal opcional):** no se lanzó `rosbridge_server` ni se abrió `testbench/index.html` en esta sesión automatizada; no hay capturas de pantalla.

## Secuencia de estados FSM observada

Orden **confirmado** en `/fsm/state` (`flightmind_msgs/msg/FSMState`, campo `current_mode`):

| Paso | Estímulo | `current_mode` observado |
|------|-----------|----------------------------|
| 1 | Arranque `mission_fsm_node` (`initial_state:=PREFLIGHT`) | **PREFLIGHT** |
| 2 | `/fsm/in/preflight_ok` true | **AUTOTAXI** |
| 3 | `/fsm/in/taxi_clear` true | **TAKEOFF** |
| 4 | `/fsm/in/takeoff_complete` true | **CRUISE** |
| 5 | `/fsm/in/daidalus_alert` `Int32` data=2 | **EVENT** |
| 6 | `/fsm/in/daidalus_alert` data=0 + `/fsm/in/event_cleared` true | **CRUISE** |
| 7 | `/fsm/in/land_command` true | **LANDING** |

Coincide con la intención del guion de maniobras (PREFLIGHT → … → CRUISE → EVENT → CRUISE → LANDING).

## PX4 SITL — ajustes respecto al comando solicitado

Comando de referencia (usuario):

```bash
cd ~/PX4-Autopilot
PX4_SYS_AUTOSTART=4001 ./build/px4_sitl_default/bin/px4 -s ROMFS/px4fmu_common/init.d-posix/rcS
```

**Problemas observados:**

1. **`SYS_AUTOSTART=4001` (Gazebo Harmonic):** falló la carga del mundo (`/default.sdf` no resuelto; Gazebo no disponible o `GZ_SIM_RESOURCE_PATH` no configurado). PX4 quedó en *Waiting for Gazebo world…* hasta timeout.
2. **`SYS_AUTOSTART=10016`:** quedó esperando simulador externo en TCP 4560 (*Waiting for simulator to accept connection*).
3. **Arranque desde el directorio fuente del repo:** sin `etc/init.d-posix/airframes` enlazado en la raíz del clon, apareció *no autostart file found …/PX4-Autopilot/etc/…*.

**Configuración que sí arrancó de forma estable:**

- Directorio de trabajo: `~/PX4-Autopilot/build/px4_sitl_default` (para resolver `etc/` del build).
- Script de arranque: ruta **absoluta** a `ROMFS/px4fmu_common/init.d-posix/rcS`.
- **`PX4_SYS_AUTOSTART=10040`** — *QuadrotorX SITL for SIH* (simulación en proceso, sin Gazebo externo).
- Criterio de “listo”: línea de log `Startup script returned successfully` (en esta versión de PX4 **no** apareció el texto literal `[param] parameter storage: /tmp/sitl_default/rootfs/eeprom/parameters` en la ventana inspeccionada; los parámetros sí se cargaron vía `parameters.bson`).

## Micro-XRCE-DDS Agent

```bash
MicroXRCEAgent udp4 -p 8888
```

Estable con mensajes del tipo *participant created* / sesión establecida tras conectar PX4 (`client_key`, `127.0.0.1`).

## Stack FlightMind

- **`ros2 launch upnext_bringup hil_sitl.launch.py`:** no se usó como único arranque porque también intenta lanzar PX4/XRCE; aquí PX4 y el agente ya estaban activos.
- **Arranque manual (equivalente al fallback del guion):** `ros2 run mission_fsm mission_fsm_node` (parámetros `initial_state`, `quality_flag_threshold`, `daidalus_alert_amber`) y `ros2 run acas_node acas_node`.
- **`navigation_bridge`:** `ros2 topic run navigation_bridge navigation_bridge_node` devolvió **No executable found** (índice ament / entorno); el binario existe en `install/navigation_bridge/bin/navigation_bridge_node` y puede ejecutarse directamente con `PYTHONPATH` que incluya `px4_msgs` si hiciera falta. No fue imprescindible para validar el FSM en esta sesión.

## Smoke test — desviación del guion original

- **DAIDALUS:** el nodo `mission_fsm` se suscribe a **`/fsm/in/daidalus_alert`** (`std_msgs/Int32`), no a `/daidalus/alert_level`. En el informe se usó `/fsm/in/daidalus_alert` con `data: 2` y `data: 0` para alinear el test con el contrato real.
- **Armado PX4:** `ros2 topic pub ... /fmu/in/vehicle_command` con `px4_msgs/msg/VehicleCommand` completó sin error (suscripción XRCE activa).

Salida completa archivada en el entorno de prueba: `/tmp/hil_smoke_output.txt`.

## Topics activos confirmados (muestra)

De `ros2 topic list`, entre otros:

- **FSM:** `/fsm/state`, y entradas bajo `/fsm/in/*` usadas en el smoke.
- **ACAS:** `/acas/advisory`.
- **PX4 (XRCE):** múltiples `/fmu/in/*` y `/fmu/out/*` (bridge DDS operativo).

## Errores o ajustes necesarios (checklist)

| Ítem | Acción recomendada |
|------|---------------------|
| Autostart 4001 + Gazebo | Instalar/configurar Gazebo Sim y variables `GZ_SIM_RESOURCE_PATH`, o fijar mundo SDF válido. |
| Comando PX4 desde `~/PX4-Autopilot` sin `etc/` | Usar `build/px4_sitl_default` como CWD o enlazar `etc` según documentación PX4. |
| `ros2 run navigation_bridge …` | Reinstalar paquete con `colcon build` y comprobar `ament_index` / `setup.bash`; o invocar el binario bajo `install/.../bin/`. |
| Guion usuario vs. software | Publicar alertas DAIDALUS en `/fsm/in/daidalus_alert` (o añadir nodo relay `/daidalus/alert_level` → `/fsm/in/daidalus_alert`). |
