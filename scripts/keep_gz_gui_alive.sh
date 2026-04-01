#!/usr/bin/env bash
# Mantiene vivo el cliente GUI de Gazebo si el servidor está activo.
set -eo pipefail

LOG_FILE="${1:-/tmp/gz_gui_reopen.log}"

while true; do
  if pgrep -af "gz sim --verbose=.*-s " >/dev/null 2>&1; then
    if ! pgrep -af "gz sim -g --render-engine ogre" >/dev/null 2>&1; then
      nohup gz sim -g --render-engine ogre >>"${LOG_FILE}" 2>&1 &
      sleep 3
    fi
  fi
  sleep 5
done
