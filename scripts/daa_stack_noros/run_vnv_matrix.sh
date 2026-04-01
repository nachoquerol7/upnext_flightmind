#!/usr/bin/env bash
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIOS=(head_on overtake crossing geofence_intrusion)

for s in "${SCENARIOS[@]}"; do
  echo "===== VNV ${s} ====="
  if "${ROOT}/run_scenario.sh" "${s}"; then
    echo "RESULT ${s}: PASS (runner ejecutado)"
  else
    echo "RESULT ${s}: FAIL"
    exit 1
  fi
done

echo "===== VNV matrix complete ====="
