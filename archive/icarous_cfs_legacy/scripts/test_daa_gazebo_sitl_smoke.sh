#!/usr/bin/env bash
# Prueba con SIMULACIÓN (Gazebo servidor + PX4 SITL + MicroXRCE): no es el test rápido de CI.
# El test colcon "test_daa_fake_stack" va SIN Gazebo (solo fake_px4).
#
# Uso (desde la raíz del workspace):
#   source /opt/ros/jazzy/setup.bash && source ~/ros2_ws/install/setup.bash
#   source install/setup.bash
#   ./scripts/test_daa_gazebo_sitl_smoke.sh
#
# Primera vez: PX4 puede compilar; export WAIT_SEC=180 si hace falta.
set -eo pipefail
set +m

WAIT_SEC="${WAIT_SEC:-90}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if ! command -v ros2 &>/dev/null; then
  echo "ERROR: activa ROS y source install/setup.bash" >&2
  exit 1
fi

# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
if [[ -f "${HOME}/ros2_ws/install/setup.bash" ]]; then
  # shellcheck source=/dev/null
  source "${HOME}/ros2_ws/install/setup.bash"
fi
# shellcheck source=/dev/null
source "${ROOT}/install/setup.bash"
# shellcheck source=/dev/null
source "${ROOT}/archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh"

cleanup() {
  set +e
  bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh" 2>/dev/null
  sleep 2
  set -e
}
trap cleanup EXIT

echo "[sim_smoke] Parando demos anteriores…"
bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh" 2>/dev/null || true
sleep 2

LOG=/tmp/upnext_daa_sim_smoke.log
echo "[sim_smoke] Lanzando daa_smoke_flying (headless, gz_x500)… (log: ${LOG})"

ros2 launch upnext_icarous_daa daa_smoke_flying.launch.py \
  headless_gz:=true \
  use_rviz:=false \
  vehicle:=gz_x500 \
  px4_gz_model_pose:="0,0,0.5,0,0,0" \
  takeoff_delay_sec:=120 \
  viz_logo_mesh:=false \
  > "${LOG}" 2>&1 &
# shellcheck disable=SC2034
LPID=$!

echo "[sim_smoke] Esperando hasta ${WAIT_SEC}s a que PX4 + uXRCE publiquen posición local…"
t0=$(date +%s)
ok=0
while true; do
  now=$(date +%s)
  if (( now - t0 >= WAIT_SEC )); then
    break
  fi
  if ros2 topic info /fmu/out/vehicle_local_position_v1 2>/dev/null | grep -q 'Publisher count: [1-9]'; then
    ok=1
    break
  fi
  sleep 3
done

if [[ "${ok}" -ne 1 ]]; then
  echo "ERROR: no hubo publisher en /fmu/out/vehicle_local_position_v1 a tiempo." >&2
  echo "Revisa ${LOG} (últimas líneas):" >&2
  tail -60 "${LOG}" >&2 || true
  exit 1
fi

echo "[sim_smoke] OK: simulación SITL + Gazebo (headless) publica posición local."
echo "[sim_smoke] Para ver 3D: gz sim -g   (otro terminal, con el launch en marcha)."
exit 0
