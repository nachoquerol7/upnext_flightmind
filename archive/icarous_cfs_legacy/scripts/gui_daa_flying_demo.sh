#!/usr/bin/env bash
# Dos ventanas: (1) Gazebo = UN solo dron PX4  (2) RViz = DAA + segundo "dron" como MARCADOR (no hay 2 modelos en Gazebo).
# Tras ~takeoff_delay_sec: ARM + despegue por MAVLink.
# Arranca MicroXRCEAgent (UDP 8888) para bridgar PX4 → ROS 2 (/fmu/out/*).
# Máquina justa: scripts/gui_daa_flying_demo_lite.sh (sin GUI gz, x500, sin RViz).
# Requisitos: ~/PX4-Autopilot construido para sim, Gazebo (gz) según PX4, px4_msgs.
#
# Ejemplos:
#   ./gui_daa_flying_demo.sh
#   ./gui_daa_flying_demo.sh vehicle:=gz_x500 takeoff_delay_sec:=90
# Sin nounset: los setup.bash de ROS usan variables opcionales.
set -eo pipefail
: "${DISPLAY:=:0}"
: "${WAYLAND_DISPLAY:=wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if pgrep -f 'daa_smoke_demo.launch.py|daa_smoke_flying.launch.py' >/dev/null 2>&1; then
  echo "Parando demo DAA anterior…" >&2
  bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh" || true
  sleep 2
fi
source /opt/ros/jazzy/setup.bash
source "${HOME}/ros2_ws/install/setup.bash"
source "${ROOT}/install/setup.bash"
source "${ROOT}/archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh"
exec ros2 launch upnext_icarous_daa daa_smoke_flying.launch.py "$@"
