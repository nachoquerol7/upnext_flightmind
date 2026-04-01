#!/usr/bin/env bash
# Graba topics del demo DAA (replay con: ros2 bag play <carpeta>).
# Lanza esto en un segundo terminal mientras corre:
#   ros2 launch upnext_icarous_daa daa_smoke_demo.launch.py
#
# Uso (desde raíz del workspace):
#   source install/setup.bash  # + ROS + px4_msgs underlay
#   ./archive/icarous_cfs_legacy/scripts/record_daa_smoke_demo.sh [nombre_salida_opcional]

# Sin nounset: compatibilidad con setup.bash de ROS
set -eo pipefail

OUT="${1:-daa_smoke_$(date +%Y%m%d_%H%M)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT}"

if ! command -v ros2 &>/dev/null; then
  echo "error: activa el entorno ROS (source install/setup.bash)" >&2
  exit 1
fi

echo "Grabando en ${OUT}.mcap (Ctrl+C para parar)…"
exec ros2 bag record -o "${OUT}" \
  /upnext_daa/daa_demo/viz_markers \
  /upnext_daa/daa_traffic_monitor/daa/bands_summary \
  /upnext_daa/fmu/out/vehicle_global_position \
  /upnext_daa/fmu/out/vehicle_local_position_v1
