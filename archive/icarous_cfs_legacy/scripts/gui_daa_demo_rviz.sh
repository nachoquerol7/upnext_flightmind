#!/usr/bin/env bash
# Demo DAA + RViz: 2 UAV (sintético), geocerca, ruta misión y evasión si DAA ve conflicto.
# Sin Gazebo. Menú de aplicaciones, terminal GNOME, o: ./gui_daa_demo_rviz.sh
set -euo pipefail
# Si no hay DISPLAY (Cursor, cron, .desktop roto), usar la sesión local típica
: "${DISPLAY:=:0}"
: "${WAYLAND_DISPLAY:=wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Un solo publisher en /fmu/out/...; si lanzas el demo 3 veces, todo se buguea.
if pgrep -f 'fake_px4_for_daa_test' >/dev/null 2>&1 || pgrep -f 'daa_smoke_demo.launch.py' >/dev/null 2>&1; then
  echo "Parando demo DAA anterior (evitar topics duplicados)…" >&2
  bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh" || true
  sleep 1
fi
source /opt/ros/jazzy/setup.bash
source "${HOME}/ros2_ws/install/setup.bash"
source "${ROOT}/install/setup.bash"
source "${ROOT}/archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh"
exec ros2 launch upnext_icarous_daa daa_smoke_demo.launch.py use_gazebo:=false use_rviz:=true
