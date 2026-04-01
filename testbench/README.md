# SIL V&V Visual Testbench (ROS2 + rosbridge)

Aplicación web **standalone** (HTML/CSS/JS + **roslibjs** por CDN) para demostración y depuración: se conecta al stack real vía **rosbridge** WebSocket y muestra señales en vivo.

## Arranque automático (recomendado)

Desde **cualquier directorio**:

```bash
bash /ruta/a/upnext_uas_ws/testbench/launch.sh
```

O haz **doble clic** en `testbench/testbench.desktop` (puede pedir marcar el ejecutable como de confianza). El script:

1. Hace `source ~/upnext_uas_ws/install/setup.bash`
2. Detiene instancias previas de rosbridge y `mission_fsm_node`
3. Lanza **rosbridge** y **`mission_fsm_node`** en segundo plano
4. Abre `testbench/index.html` en el navegador
5. Arranca `ram_monitor.py` en **localhost:9091** (RAM por proceso para el panel **MemoryPanel** / TC-E2E-007). Opcional: `pip install psutil` para listar procesos; sin `psutil` el endpoint responde `[]`.

Cada **TC** del sidebar monta un **panel visual** distinto (FSM, mapa, radar DAIDALUS, latencia, watchdog, E2E compuesto, memoria). Al terminar un TC con **Run TC**, el panel muestra **PASS/FAIL** con evidencia y **Limpiar** para volver al modo en vivo.

Para detener los nodos ROS, cierra la terminal donde corre `launch.sh` (o Ctrl+C). En el testbench, **Stop stack** solo cierra el cliente WebSocket en el navegador; si el bridge se cae solo, el log muestra: *Stack detenido. Ejecuta launch.sh para reiniciar.*

## Requisitos

- ROS 2 (Humble o Jazzy)
- Paquete `rosbridge_suite`
- Stack publicando los topics listados abajo (p. ej. `mission_fsm`, sensores simulados, etc.)

## Arranque

```bash
# Instalar rosbridge (ejemplo Humble)
sudo apt install ros-humble-rosbridge-suite

# Jazzy
sudo apt install ros-jazzy-rosbridge-suite
```

Lanzar el servidor WebSocket (puerto por defecto **9090**):

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

Abrir el testbench **sin servidor HTTP** (protocolo `file://` o sirviendo la carpeta si el navegador bloquea file+WebSocket):

```bash
firefox /ruta/al/ws/testbench/index.html
# o
xdg-open testbench/index.html
```

Si `roslib` no conecta desde `file://`, sirve la carpeta con un servidor estático mínimo:

```bash
cd testbench && python3 -m http.server 8080
# firefox http://127.0.0.1:8080/
```

## Topics suscritos (según `js/app.js`)

| Topic | Tipo (roslib) |
|-------|----------------|
| `/fsm/state` | `flightmind_msgs/FSMState` |
| `/fsm/current_mode` | `std_msgs/String` |
| `/nav/quality_flag` | `std_msgs/Float64` |
| `/daidalus/alert_level` | `std_msgs/Int32` |
| `/fdir/emergency` | `std_msgs/Bool` |
| `/fdir/status` | `std_msgs/String` |
| `/fdir/active_fault` | `std_msgs/String` |
| `/vehicle_model/state` | `std_msgs/Float64MultiArray` |

Si tu distro usa nombres de tipo distintos (`std_msgs/msg/Bool` vs `std_msgs/Bool`), ajusta los strings en `js/app.js`.

## Topics publicados por los TCs (ejemplos)

`/fsm/in/preflight_ok`, `taxi_clear`, `takeoff_complete`, `quality_flag`, `daidalus_alert`, `rtb_command`, `land_command`, `event_cleared`, `fdir_emergency`, `abort_command`, etc. (`std_msgs`).

## Módulos

- **M1** — Grafo FSM + TCs de transición
- **M4** — Mapa 2D + perfil de altitud (desde `/vehicle_model/state`)
- **M5** — DAIDALUS (visual + TCs de nivel de alerta)
- **M6** — FDIR (árbol + TCs)
- **M7** — Nav2 / mapa referencia
- **M9** — E2E resumen

Los módulos M2, M3, M8 y M10 muestran placeholders hasta cablear más TCs.
