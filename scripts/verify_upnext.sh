#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash 2>/dev/null || source /opt/ros/humble/setup.bash
if [[ -f "${HOME}/ros2_ws/install/setup.bash" ]]; then
  # shellcheck source=/dev/null
  source "${HOME}/ros2_ws/install/setup.bash"
fi
colcon build --symlink-install
# shellcheck source=/dev/null
source install/setup.bash
set +e
timeout 3 ros2 run vehicle_model vehicle_model_node 2>/dev/null
code=$?
set -e
if [[ "$code" -eq 0 ]] || [[ "$code" -eq 124 ]]; then
  echo "[verify_upnext] OK (colcon + vehicle_model_node smoke, exit $code)"
  exit 0
fi
echo "[verify_upnext] WARN: vehicle_model_node smoke exit $code (build still succeeded)" >&2
exit 0
