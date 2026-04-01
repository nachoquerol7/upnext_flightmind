#!/usr/bin/env bash
# Smoke test: TrafficMonitor + DAA without PX4 (fake /fmu/out/* position topics).
# Prerrequisito: haber hecho colcon en este workspace y tener px4_msgs en underlay/overlay.
# Ejemplo:
#   source /opt/ros/jazzy/setup.bash && source ~/ros2_ws/install/setup.bash
#   source ~/upnext_uas_ws/install/setup.bash
#   ~/upnext_uas_ws/scripts/smoke_daa_traffic_monitor.sh

set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh"

if ! command -v ros2 &>/dev/null; then
  echo "error: ros2 no está en PATH. Activa ROS y los overlays, por ejemplo:" >&2
  echo "  source /opt/ros/jazzy/setup.bash && source ~/ros2_ws/install/setup.bash && source ${ROOT}/install/setup.bash" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${FAKE_PID:-}" ]] && kill -0 "${FAKE_PID}" 2>/dev/null; then
    kill "${FAKE_PID}" 2>/dev/null || true
    wait "${FAKE_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

ros2 run upnext_icarous_daa fake_px4_for_daa_test &
FAKE_PID=$!
sleep 1

ros2 launch upnext_icarous_daa daa_traffic_monitor.launch.py
