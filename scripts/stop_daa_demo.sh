#!/usr/bin/env bash
# Delegates to archived ICAROUS demo stop script (Fase 0).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${ROOT}/archive/icarous_cfs_legacy/scripts/stop_daa_demo.sh"
