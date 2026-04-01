#!/usr/bin/env bash
set -eo pipefail
if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  DIST=jazzy
elif [[ -f /opt/ros/humble/setup.bash ]]; then
  DIST=humble
else
  echo "No ROS 2 jazzy/humble encontrado en /opt/ros" >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y \
  "ros-${DIST}-ompl" \
  python3-pytest \
  python3-colcon-common-extensions
echo "[install_deps_phase0] OK (ros-${DIST}-ompl + pytest + colcon)"
