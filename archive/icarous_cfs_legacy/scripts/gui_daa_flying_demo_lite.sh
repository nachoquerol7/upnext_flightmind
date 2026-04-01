#!/usr/bin/env bash
# Modo ligero (ThinkPad / GPU limitada): sin ventana Gazebo 3D, sin RViz, multicóptero x500,
# spawn en suelo (evita caída libre antes de ARM con takeoff_delay largo), MicroXRCEAgent activo.
# Para ver 3D abre gz manual: gz sim -g  (opcional).
# Sin nounset: los setup.bash de ROS usan variables opcionales (p. ej. AMENT_TRACE_SETUP_FILES).
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
if [[ -f "${HOME}/ros2_ws/install/setup.bash" ]]; then
  source "${HOME}/ros2_ws/install/setup.bash"
fi
source "${ROOT}/install/setup.bash"
source "${ROOT}/archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh"
exec ros2 launch upnext_icarous_daa daa_smoke_flying.launch.py \
  headless_gz:=true \
  use_rviz:=false \
  vehicle:=gz_x500 \
  px4_gz_model_pose:="0,0,0.5,0,0,0" \
  takeoff_delay_sec:=35 \
  viz_logo_mesh:=false \
  "$@"
