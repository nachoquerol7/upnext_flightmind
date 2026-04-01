#!/usr/bin/env bash
# Source from workspace root: source archive/icarous_cfs_legacy/scripts/setup_icarous_env.sh
_UPNEXT_WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ICAROUS_HOME="${_UPNEXT_WS}/third_party/icarous"
export LD_LIBRARY_PATH="${ICAROUS_HOME}/Modules/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "ICAROUS_HOME=${ICAROUS_HOME}"
