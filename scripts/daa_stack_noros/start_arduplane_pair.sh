#!/usr/bin/env bash
set -eo pipefail

if [[ -z "${ARDUPILOT_HOME:-}" ]]; then
  echo "ERROR: export ARDUPILOT_HOME=~/ardupilot" >&2
  exit 1
fi

SIM_VEHICLE="${ARDUPILOT_HOME}/Tools/autotest/sim_vehicle.py"
if [[ ! -f "${SIM_VEHICLE}" ]]; then
  echo "ERROR: no existe ${SIM_VEHICLE}" >&2
  exit 2
fi

echo "[start_arduplane_pair] ARDUPILOT_HOME=${ARDUPILOT_HOME}"
echo "[start_arduplane_pair] Lanzando dos instancias ArduPlane SITL..."

# Instancia ownship: MAVLink principal en 14550
nohup python3 "${SIM_VEHICLE}" -v ArduPlane -I0 --map --console \
  --out=udp:127.0.0.1:14550 \
  > /tmp/arduplane_ownship.log 2>&1 &

sleep 2

# Instancia intruder: MAVLink en 14560
nohup python3 "${SIM_VEHICLE}" -v ArduPlane -I1 --map --console \
  --out=udp:127.0.0.1:14560 \
  > /tmp/arduplane_intruder.log 2>&1 &

sleep 2

echo "[start_arduplane_pair] Logs:"
echo "  - /tmp/arduplane_ownship.log"
echo "  - /tmp/arduplane_intruder.log"
echo "[start_arduplane_pair] Puertos MAVLink esperados:"
echo "  - ownship: udp://127.0.0.1:14550"
echo "  - intruder: udp://127.0.0.1:14560"
