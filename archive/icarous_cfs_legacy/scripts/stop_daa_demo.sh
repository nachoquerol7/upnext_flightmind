#!/usr/bin/env bash
# Para demo DAA + (opcional) PX4 SITL / Gazebo si quedaron colgados.
set -euo pipefail
pkill -9 -f 'daa_smoke_demo.launch.py' 2>/dev/null || true
pkill -9 -f 'daa_smoke_flying.launch.py' 2>/dev/null || true
pkill -9 -f 'fake_px4_for_daa_test' 2>/dev/null || true
pkill -9 -f 'daa_demo_viz' 2>/dev/null || true
pkill -9 -f 'daa_traffic_monitor_node' 2>/dev/null || true
pkill -9 -f 'ros2 launch upnext_icarous_daa' 2>/dev/null || true
pkill -9 -f 'rviz2.*daa_smoke_demo' 2>/dev/null || true
# PX4 + Gazebo (si no se paran, el siguiente px4_sitl dice "server already running")
pkill -9 -f 'px4_sitl_default/bin/px4' 2>/dev/null || true
pkill -9 -f 'make -C.*PX4-Autopilot.*px4_sitl' 2>/dev/null || true
pkill -9 -x 'gz sim' 2>/dev/null || true
pkill -9 -f 'gz sim ' 2>/dev/null || true
pkill -9 -f 'MicroXRCEAgent' 2>/dev/null || true
sleep 2
echo "Demo DAA parado (PX4 SITL, gz, MicroXRCEAgent si estaban activos)."
