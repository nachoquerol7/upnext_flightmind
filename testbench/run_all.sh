#!/usr/bin/env bash
# Orquestador SIL: ROS2 Jazzy + rosbridge + proxy LLM + HTTP estático + Firefox.
# Sin -u: los setup.bash de ROS/workspace referencian variables aún no definidas.
set -eo pipefail

WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WS_ROOT" || exit 1

CHILD_PIDS=()

cleanup() {
  local pid
  for pid in $(jobs -p); do
    kill "$pid" 2>/dev/null || true
  done
  echo ""
  echo "Deteniendo servicios del testbench..."
  for pid in "${CHILD_PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  pkill -f "ros2 launch mission_fsm flight_demo.launch.py" 2>/dev/null || true
  pkill -f "llm_proxy.js" 2>/dev/null || true
  pkill -f "[p]ython3 -m http.server --directory ${WS_ROOT}/testbench" 2>/dev/null || true
}

trap 'cleanup' EXIT INT TERM HUP

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "ERROR: ROS 2 Jazzy no encontrado en /opt/ros/jazzy/setup.bash" >&2
  exit 1
fi
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
if [[ ! -f "$WS_ROOT/install/setup.bash" ]]; then
  echo "ERROR: Falta $WS_ROOT/install/setup.bash (coloca el workspace o ejecuta colcon build)." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$WS_ROOT/install/setup.bash"

echo "Iniciando ros2 launch (rosbridge)..."
ros2 launch mission_fsm flight_demo.launch.py include_rosbridge:=true &
CHILD_PIDS+=($!)

echo "Iniciando llm_proxy (requiere ANTHROPIC_API_KEY en el entorno)..."
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "  (aviso: ANTHROPIC_API_KEY vacía; el proxy puede salir al instante)" >&2
fi
node "$WS_ROOT/testbench/llm_proxy.js" &
CHILD_PIDS+=($!)

HTTP_LOG="$WS_ROOT/testbench/http_server.log"
: >"$HTTP_LOG"
echo "Sirviendo testbench en http://localhost:8000 (log: testbench/http_server.log) ..."
python3 -m http.server --directory "$WS_ROOT/testbench" 8000 >>"$HTTP_LOG" 2>&1 &
CHILD_PIDS+=($!)

echo "Esperando 3 s a que suba el stack..."
sleep 3

if command -v firefox >/dev/null 2>&1; then
  firefox "http://localhost:8000" >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:8000" >/dev/null 2>&1 &
else
  echo "Abre manualmente: http://localhost:8000" >&2
fi

echo "Listo. Terminal: salida ROS2 / LLM. Cierra aquí o Ctrl+C para detener todo."
wait
