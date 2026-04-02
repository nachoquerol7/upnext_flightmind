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
APT_PKGS=(
  "ros-${DIST}-ompl"
  python3-pytest
  python3-colcon-common-extensions
)
# rosbridge_suite en src/ (CMake) lo pide al compilar mission_fsm / testbench
if apt-cache show "ros-${DIST}-ament-cmake-mypy" &>/dev/null; then
  APT_PKGS+=("ros-${DIST}-ament-cmake-mypy")
fi
sudo apt-get install -y "${APT_PKGS[@]}"
echo "[install_deps_phase0] OK (ros-${DIST}-ompl + pytest + colcon + ament_cmake_mypy si existe)"
