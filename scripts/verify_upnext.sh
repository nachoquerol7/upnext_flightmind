#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
# shellcheck source=/dev/null
source install/setup.bash
# shellcheck source=/dev/null
source scripts/setup_icarous_env.sh
set +e
timeout 3 ros2 run upnext_icarous_bridge icarous_bridge_node --ros-args -p publish_hz:=0.0
code=$?
set -e
# 124 = timeout (expected for this smoke test)
if [[ "$code" -eq 0 ]] || [[ "$code" -eq 124 ]]; then
  echo "[verify_upnext] OK (colcon + icarous_bridge smoke, exit $code)"
  exit 0
fi
exit "$code"
