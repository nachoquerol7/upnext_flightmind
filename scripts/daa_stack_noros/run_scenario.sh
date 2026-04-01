#!/usr/bin/env bash
set -eo pipefail

SCENARIO="${1:-}"
if [[ -z "${SCENARIO}" ]]; then
  echo "Uso: $0 <head_on|overtake|crossing|geofence_intrusion>" >&2
  exit 1
fi

case "${SCENARIO}" in
  head_on)
    INTR_N0=220; INTR_E0=0; INTR_VN=-8; INTR_VE=0; EXPECT="CONFLICT_ENTER"
    ;;
  overtake)
    INTR_N0=-260; INTR_E0=0; INTR_VN=9; INTR_VE=0; EXPECT="CONFLICT_ENTER"
    ;;
  crossing)
    INTR_N0=0; INTR_E0=260; INTR_VN=0; INTR_VE=-8; EXPECT="CONFLICT_ENTER"
    ;;
  geofence_intrusion)
    INTR_N0=0; INTR_E0=260; INTR_VN=0; INTR_VE=-6; EXPECT="GEOFENCE_INTRUSION+CONFLICT_ENTER"
    ;;
  *)
    echo "Escenario desconocido: ${SCENARIO}" >&2
    exit 2
    ;;
esac

OUT_JSON="/tmp/daa_noros_${SCENARIO}.json"
cat > "${OUT_JSON}" <<EOF
{
  "scenario": "${SCENARIO}",
  "ownship_mavlink": "udp://127.0.0.1:14550",
  "intruder_mode": "synthetic",
  "intruder_initial_EN_m": {"n": ${INTR_N0}, "e": ${INTR_E0}},
  "intruder_velocity_NE_mps": {"vn": ${INTR_VN}, "ve": ${INTR_VE}},
  "expected": "${EXPECT}",
  "notes": "No ROS. ArduPilot + ICAROUS/DAIDALUS + PolyCARP."
}
EOF

echo "[run_scenario] Escenario: ${SCENARIO}"
echo "[run_scenario] Config: ${OUT_JSON}"

if [[ -n "${ICAROUS_MAVLINK_BRIDGE_CMD:-}" ]]; then
  echo "[run_scenario] Ejecutando ICAROUS bridge..."
  echo "[run_scenario] CMD=${ICAROUS_MAVLINK_BRIDGE_CMD}"
  # shellcheck disable=SC2086
  eval ${ICAROUS_MAVLINK_BRIDGE_CMD}
else
  echo "[run_scenario] ICAROUS_MAVLINK_BRIDGE_CMD no definido."
  echo "[run_scenario] Exportalo para ejecutar lazo completo con MAVLink."
fi
