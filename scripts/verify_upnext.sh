#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
# shellcheck source=/dev/null
source install/setup.bash
# shellcheck source=/dev/null
source scripts/setup_icarous_env.sh
exec timeout 3 ros2 run upnext_icarous_bridge icarous_bridge_node --ros-args -p publish_hz:=0.0
