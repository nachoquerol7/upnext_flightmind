#!/bin/bash
unset COLCON_TRACE
set -euo pipefail

TB_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$TB_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$TB_DIR/.env"
  set +a
fi

source "$HOME/upnext_uas_ws/install/setup.bash"

# Matar instancias previas
pkill -f rosbridge_websocket || true
pkill -f mission_fsm_node || true
pkill -f "ram_monitor.py" || true
pkill -f "llm_proxy.js" || true
sleep 1

LLM_PID=""
cleanup() {
  if [ -n "${LLM_PID:-}" ]; then
    kill "$LLM_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "[launch] Arrancando LLM proxy en :3001..."
  node "$TB_DIR/llm_proxy.js" &
  LLM_PID=$!
  echo "[launch] LLM proxy PID: $LLM_PID"
else
  echo "[launch] ANTHROPIC_API_KEY no definida — LLM Analyst desactivado."
  echo "[launch] Para activarlo: ANTHROPIC_API_KEY=sk-... bash testbench/launch.sh"
fi

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
python3 "$TB_DIR/ram_monitor.py" &
echo "ram_monitor PID: $!"

# Abrir el testbench en el navegador
xdg-open "$TB_DIR/index.html"

echo "Stack arrancado (rosbridge + mission_fsm + ram_monitor). Cierra esta terminal para parar todo."
wait
