#!/usr/bin/env bash
# Arranca demo DAA + RViz en tu sesión gráfica (:0) y deja log en /tmp/upnext_daa_rviz.log
# Uso: ./start_daa_rviz_demo.sh          — normal
#      VIZ_LITE=1 ./start_daa_rviz_demo.sh — sin mesh del logo si RViz/GPU petaba
set -euo pipefail
: "${DISPLAY:=:0}"
: "${WAYLAND_DISPLAY:=wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh" >/dev/null 2>&1 || true
sleep 1
LOG=/tmp/upnext_daa_rviz.log
EXTRA=()
if [[ "${VIZ_LITE:-0}" == "1" ]]; then
  EXTRA+=(viz_logo_mesh:=false)
fi
(
  source /opt/ros/jazzy/setup.bash
  source "${HOME}/ros2_ws/install/setup.bash"
  source "${ROOT}/install/setup.bash"
  source "${ROOT}/archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh"
  exec ros2 launch upnext_icarous_daa daa_smoke_demo.launch.py use_gazebo:=false use_rviz:=true "${EXTRA[@]}" "$@"
) >>"${LOG}" 2>&1 &

echo "Demo lanzada en segundo plano. Log: ${LOG}"
echo "Para ver errores: tail -f ${LOG}"
echo "Para parar: pkill -f 'daa_smoke_demo.launch.py' ; pkill rviz2"
