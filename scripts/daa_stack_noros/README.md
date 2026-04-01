# DAA Stack No-ROS (ArduPilot + ICAROUS)

Arquitectura objetivo (sin ROS/PX4/Gazebo):

- Simulacion/autopiloto: ArduPlane SITL (2 instancias MAVLink).
- Decision DAA: ICAROUS (DAIDALUS + PolyCARP) por MAVLink nativo.
- Visualizacion operacional: Mission Planner.
- Visualizacion analitica: dashboard matplotlib propio.
- Intruder: sintetico (inyectado en ICAROUS).

## Estado actual de esta carpeta

Esta carpeta reemplaza el flujo ROS/PX4 con un esqueleto operativo no-ROS:

- `stop_all.sh`: para procesos legacy (ROS/PX4/Gazebo) y ArduPilot.
- `start_arduplane_pair.sh`: lanza 2 SITL de ArduPlane via `sim_vehicle.py`.
- `run_scenario.sh`: runner comun para escenarios V&V.
- `scenario_*.sh`: 4 escenarios minimos defendibles (head-on, overtake, crossing, geofence).
- `run_vnv_matrix.sh`: ejecuta los cuatro en cadena.

## Requisitos

1) Tener ArduPilot clonado:

```bash
git clone https://github.com/ArduPilot/ardupilot.git ~/ardupilot
```

2) Exportar la ruta:

```bash
export ARDUPILOT_HOME=~/ardupilot
```

3) Tener `sim_vehicle.py` funcional (dependencias de ArduPilot instaladas).

## Uso rapido

```bash
cd ~/upnext_uas_ws
./scripts/daa_stack_noros/stop_all.sh
./scripts/daa_stack_noros/start_arduplane_pair.sh
./scripts/daa_stack_noros/run_vnv_matrix.sh
```

## Nota importante

`run_scenario.sh` deja la configuracion de cada escenario en `/tmp/daa_noros_<escenario>.json`
y prepara la ejecucion para ICAROUS por MAVLink.

Para acoplar el ejecutable/comando exacto de ICAROUS en tu entorno, exporta:

```bash
export ICAROUS_MAVLINK_BRIDGE_CMD="<comando real para lanzar ICAROUS con MAVLink>"
```

Ejemplo (placeholder, adaptar a tu build real):

```bash
export ICAROUS_MAVLINK_BRIDGE_CMD="$ICAROUS_HOME/exe/cpu1/core-cpu1 -C 1 -I 0"
```
