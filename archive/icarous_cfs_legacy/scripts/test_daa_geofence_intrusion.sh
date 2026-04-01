#!/usr/bin/env bash
# Test de intrusión en geofence para DAIDALUS/ICAROUS en SITL.
# Criterio PASS:
#  1) El intruder cruza desde fuera hacia dentro del geofence nominal EN:
#     N in [-120,220], E in [-120,120]
#  2) Aparece numConflictTraffic >= 1 en /upnext_daa/.../bands_summary.
set -eo pipefail
set +m

WAIT_PUB_SEC="${WAIT_PUB_SEC:-90}"
WAIT_CONFLICT_SEC="${WAIT_CONFLICT_SEC:-140}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if ! command -v ros2 >/dev/null 2>&1; then
  echo "ERROR: activa ROS 2 y source install/setup.bash" >&2
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

echo "[geofence] Parando demos anteriores..."
bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh" 2>/dev/null || true
sleep 2

LOG=/tmp/upnext_daa_geofence_intrusion.log
echo "[geofence] Lanzando escenario intrusión geofence (headless) ... log: ${LOG}"

# Intruder: fuera del geofence por el Este y entrando hacia el interior.
INTR_N0=0
INTR_E0=260
INTR_VN=0
INTR_VE=-6
GF_N_MIN=-120
GF_N_MAX=220
GF_E_MIN=-120
GF_E_MAX=120

ros2 launch upnext_icarous_daa daa_smoke_flying.launch.py \
  headless_gz:=true \
  use_rviz:=false \
  vehicle:=gz_x500 \
  px4_gz_world:=daa_vfr_landmarks \
  px4_gz_model_pose:="0,0,0.5,0,0,0" \
  auto_takeoff:=true \
  auto_arm_only:=false \
  takeoff_delay_sec:=8 \
  takeoff_alt:=30 \
  auto_set_offboard:=true \
  offboard_delay_sec:=12 \
  offboard_enable:=true \
  resolution_climb_m:=2.0 \
  intruder_n_m:=${INTR_N0} \
  intruder_e_m:=${INTR_E0} \
  intruder_vn:=${INTR_VN} \
  intruder_ve:=${INTR_VE} \
  intruder_vd:=0 \
  viz_logo_mesh:=false \
  > "${LOG}" 2>&1 &

echo "[geofence] Esperando publishers PX4 (timeout ${WAIT_PUB_SEC}s)..."
t0=$(date +%s)
pub_ok=0
while true; do
  now=$(date +%s)
  if (( now - t0 >= WAIT_PUB_SEC )); then
    break
  fi
  info="$(ros2 topic info /fmu/out/vehicle_local_position_v1 2>/dev/null || true)"
  if [[ "${info}" == *"Publisher count: 1"* ]] || [[ "${info}" == *"Publisher count: 2"* ]] || [[ "${info}" == *"Publisher count: 3"* ]]; then
    pub_ok=1
    break
  fi
  sleep 2
done

if [[ "${pub_ok}" -ne 1 ]]; then
  echo "FAIL: no hubo publisher PX4 en /fmu/out/vehicle_local_position_v1." >&2
  echo "Revisa log: ${LOG}" >&2
  exit 2
fi

echo "[geofence] Esperando intrusión + conflicto DAA (timeout ${WAIT_CONFLICT_SEC}s)..."
t1=$(date +%s)
intrusion_ok=0
conflict_ok=0
while true; do
  now=$(date +%s)
  elapsed=$(( now - t1 ))
  if (( elapsed >= WAIT_CONFLICT_SEC )); then
    break
  fi

  # Detección analítica de cruce del intruder al geofence (modelo cinemático del escenario)
  e_now="$(python3 -c 'import sys; e0=float(sys.argv[1]); ve=float(sys.argv[2]); t=float(sys.argv[3]); print(e0 + ve*t)' "${INTR_E0}" "${INTR_VE}" "${elapsed}")"
  n_now="$(python3 -c 'import sys; n0=float(sys.argv[1]); vn=float(sys.argv[2]); t=float(sys.argv[3]); print(n0 + vn*t)' "${INTR_N0}" "${INTR_VN}" "${elapsed}")"
  inside="$(python3 -c 'import sys; n=float(sys.argv[1]); e=float(sys.argv[2]); nmin=float(sys.argv[3]); nmax=float(sys.argv[4]); emin=float(sys.argv[5]); emax=float(sys.argv[6]); print(1 if (nmin <= n <= nmax and emin <= e <= emax) else 0)' "${n_now}" "${e_now}" "${GF_N_MIN}" "${GF_N_MAX}" "${GF_E_MIN}" "${GF_E_MAX}")"
  if [[ "${inside}" == "1" ]]; then
    intrusion_ok=1
  fi

  msg="$(timeout 4 ros2 topic echo /upnext_daa/daa_traffic_monitor/daa/bands_summary --once 2>/dev/null || true)"
  if [[ -n "${msg}" ]]; then
    data_line="$(printf '%s\n' "${msg}" | awk '/^data:/ {print; exit}')"
    first_val="$(python3 -c 'import re,sys; s=sys.stdin.read(); m=re.search(r"data:\s*\[\s*([-+]?\d+(?:\.\d+)?)", s); print(m.group(1) if m else "")' <<< "${data_line}")"
    if [[ -n "${first_val}" ]]; then
      is_conflict="$(python3 -c 'import sys; v=float(sys.argv[1]); print(1 if v >= 1.0 else 0)' "${first_val}")"
      if [[ "${is_conflict}" == "1" ]]; then
        conflict_ok=1
      fi
    fi
  fi

  if [[ "${intrusion_ok}" == "1" && "${conflict_ok}" == "1" ]]; then
    break
  fi
  sleep 1
done

if [[ "${intrusion_ok}" != "1" ]]; then
  echo "FAIL: el intruder no llegó a entrar en el geofence dentro del timeout." >&2
  echo "Revisa log: ${LOG}" >&2
  exit 3
fi

if [[ "${conflict_ok}" != "1" ]]; then
  echo "FAIL: hubo intrusión geofence pero sin numConflictTraffic>=1 a tiempo." >&2
  echo "Revisa log: ${LOG}" >&2
  exit 4
fi

echo "PASS: intrusión de geofence + conflicto DAA detectados."
echo "Log: ${LOG}"
exit 0
