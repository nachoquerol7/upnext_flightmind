# Testbench visual — ejecución (2026-04-01)

## Prerrequisitos

- `sudo apt install ros-jazzy-rosbridge-suite` (obligatorio para `ros2 launch rosbridge_server …`).
- Stack ROS2 con `mission_fsm` publicando `/fsm/state`.

## Cambios en el repo

- `testbench/launch.sh`: añadido **`unset COLCON_TRACE`** antes de `set -euo pipefail` para evitar fallos si la variable no está definida con `set -u`.
- `testbench/start_rosbridge_only.sh`: arranca **solo** rosbridge (no mata `mission_fsm`). Usar en paralelo con PX4 SITL + FSM ya corriendo. **`launch.sh` completo** sigue matando `mission_fsm` al inicio — no usarlo si quieres conservar el stack previo.

## Respuestas a la checklist de verificación

1. **¿Indicador verde (“ROS2 connected”)?**  
   **No verificado aquí:** `rosbridge_server` no estaba instalado; el launch falló con `Package 'rosbridge_server' not found`. Tras instalar el paquete apt y ejecutar `start_rosbridge_only.sh`, el WebSocket en **9090** debería permitir que el testbench (roslibjs) pase a verde.

2. **¿Animación del grafo FSM?**  
   **No observado en esta sesión** (sin rosbridge / sin navegador automatizado). Con rosbridge y topics publicándose, el testbench debería reflejar `current_mode` en `/fsm/state`.

3. **Consola del navegador (F12)**  
   No capturada. Errores típicos si el indicador sigue rojo: WebSocket bloqueado (firewall), `ws://localhost:9090` incorrecto, o rosbridge no escuchando.

## Secuencia de demo (topic correcto para DAIDALUS)

Sustituir `/daidalus/alert_level` por:

```bash
ros2 topic pub --once /fsm/in/daidalus_alert std_msgs/msg/Int32 '{data: 2}'
# …
ros2 topic pub --once /fsm/in/daidalus_alert std_msgs/msg/Int32 '{data: 0}'
```

El resto de publicaciones (`/fsm/in/preflight_ok`, etc.) coinciden con el nodo.
