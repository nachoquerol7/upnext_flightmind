#!/usr/bin/env bash
# Test 1 CI (integración ligera): demo DAA con fake PX4 — sin Gazebo, sin RViz.
# Simulación física (Gazebo+PX4): ver archive/icarous_cfs_legacy/scripts/test_daa_gazebo_sitl_smoke.sh
# Valida que el TrafficMonitor publica bandas en ROS 2.
# Ejecuta: colcon test --packages-select upnext_icarous_daa
# Manual: desde la raíz del workspace con install + ROS sourcados:
#   ./src/upnext_icarous_daa/test/test_daa_fake_stack.sh
set -eo pipefail
# Evita mensajes "Killed" en stderr al parar ros2 launch (run_test.py lo marca como fallo).
set +m

# test/ → paquete → src → raíz workspace
WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${WS_ROOT}"

if ! command -v ros2 &>/dev/null; then
  echo "ERROR: ros2 no en PATH. Activa Jazzy + install/setup.bash" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${WS_ROOT}/archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh"

cleanup() {
  set +e
  bash "${WS_ROOT}/scripts/stop_daa_demo.sh" 2>/dev/null
  sleep 1
  set -e
}
trap cleanup EXIT

echo "[test_daa_fake_stack] Lanzando daa_smoke_demo (use_gazebo:=false)…"
ros2 launch upnext_icarous_daa daa_smoke_demo.launch.py \
  use_gazebo:=false \
  use_rviz:=false \
  auto_takeoff:=false \
  viz_logo_mesh:=false \
  > /tmp/upnext_daa_test_launch.log 2>&1 &
LAUNCH_PID=$!

# Arranque nodos + fake_px4
sleep 10

if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
  echo "ERROR: el launch murió antes de tiempo. Log:" >&2
  tail -80 /tmp/upnext_daa_test_launch.log >&2 || true
  exit 1
fi

BANDS="/upnext_daa/daa_traffic_monitor/daa/bands_summary"
echo "[test_daa_fake_stack] Esperando un mensaje en ${BANDS}…"

if ! timeout 25 ros2 topic echo "${BANDS}" --once > /tmp/upnext_daa_bands_once.txt 2>&1; then
  echo "ERROR: no se recibió bands_summary (timeout)." >&2
  ros2 topic list 2>&1 | grep -E 'daa|fmu' >&2 || true
  tail -80 /tmp/upnext_daa_test_launch.log >&2 || true
  exit 1
fi

if ! grep -qE '^(data:|layout:)' /tmp/upnext_daa_bands_once.txt; then
  echo "ERROR: Float64MultiArray no reconocido en bands_summary:" >&2
  cat /tmp/upnext_daa_bands_once.txt >&2
  exit 1
fi

echo "[test_daa_fake_stack] OK: TrafficMonitor publica bandas DAA."
exit 0
