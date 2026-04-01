#!/bin/bash
set -euo pipefail

source "$HOME/upnext_uas_ws/install/setup.bash"

# Matar instancias previas
pkill -f rosbridge_websocket || true
pkill -f mission_fsm_node || true
pkill -f "ram_monitor.py" || true
sleep 1

# Arrancar rosbridge en background
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &
ROSBRIDGE_PID=$!
echo "rosbridge PID: $ROSBRIDGE_PID"

# Esperar a que rosbridge esté listo
sleep 3

# Arrancar mission_fsm_node en background
ros2 run mission_fsm mission_fsm_node &
FSM_PID=$!
echo "mission_fsm PID: $FSM_PID"

sleep 1

# Monitor RAM para MemoryPanel (TC-E2E-007)
python3 "$(dirname "$0")/ram_monitor.py" &
echo "ram_monitor PID: $!"

# Abrir el testbench en el navegador
xdg-open "$(dirname "$0")/index.html"

echo "Stack arrancado (rosbridge + mission_fsm + ram_monitor). Cierra esta terminal para parar todo."
wait
