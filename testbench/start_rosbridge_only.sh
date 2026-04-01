#!/usr/bin/env bash
# Arranca solo rosbridge (no mata mission_fsm). Útil con PX4 SITL + stack ya en marcha.
unset COLCON_TRACE
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/upnext_uas_ws/install/setup.bash"

pkill -f rosbridge_websocket_launch 2>/dev/null || true
sleep 1

ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
echo "rosbridge lanzado en background (puerto 9090 por defecto). PID: $!"
sleep 3
if ss -tlnp 2>/dev/null | grep -q 9090; then echo "rosbridge OK (9090)"; else echo "rosbridge: puerto 9090 no detectado — ¿instalado ros-jazzy-rosbridge-suite?"; fi
