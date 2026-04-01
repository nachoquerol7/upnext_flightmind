#!/usr/bin/env bash
set -eo pipefail

echo "[stop_all] Parando stack legacy (ROS/PX4/Gazebo) y no-ROS (ArduPilot/ICAROUS)..."

pkill -f 'ros2 launch upnext_icarous_daa|px4_sitl|PX4-Autopilot|MicroXRCEAgent|gz sim|daa_smoke_flying.launch.py|daa_smoke_demo.launch.py' 2>/dev/null || true
pkill -f 'sim_vehicle.py|arduplane|ArduPlane|MAVProxy.py|mavproxy.py|icarous|core-cpu1' 2>/dev/null || true

sleep 1

if pgrep -af 'ros2|px4|gz sim|sim_vehicle.py|arduplane|MAVProxy|icarous|core-cpu1' >/dev/null 2>&1; then
  echo "[stop_all] Aviso: quedan procesos activos, revisa manualmente con pgrep."
else
  echo "[stop_all] OK: stack detenido."
fi
