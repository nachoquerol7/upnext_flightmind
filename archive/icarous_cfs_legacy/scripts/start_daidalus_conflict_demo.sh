#!/usr/bin/env bash
# Arranque robusto para demo DAIDALUS + ICAROUS con conflicto forzado.
# - Gazebo servidor headless (estable en GPUs problemáticas)
# - Visualización principal en RViz
# - OFFBOARD automático + resolución DAA activa

set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Limpia procesos anteriores de la demo
bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh" || true
sleep 2

bash "${ROOT}/archive/icarous_cfs_legacy/scripts/gui_daa_flying_demo.sh" \
  headless_gz:=false \
  use_rviz:=true \
  px4_gz_world:=daa_vfr_landmarks \
  px4_gz_model_pose:="0,0,0.5,0,0,0" \
  auto_takeoff:=true \
  auto_arm_only:=false \
  takeoff_delay_sec:=8 \
  takeoff_alt:=30 \
  auto_set_offboard:=true \
  resolution_climb_m:=2.0 \
  intruder_n_m:=50 \
  intruder_e_m:=0 \
  intruder_vn:=0 \
  intruder_ve:=-4 \
  intruder_vd:=0 \
  "$@"
