#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${ROOT}"
mkdir -p "${DEST}"
cd "${DEST}"
OK=0
for pra in 0 1 2 3 4; do
  for tau in 00 01 02 03 04 05 06 07 08; do
    name="HCAS_rect_v6_pra${pra}_tau${tau}_25HU_3000it.nnet"
    if wget -q "https://raw.githubusercontent.com/sisl/HorizontalCAS/master/GenerateNetworks/networks/${name}"; then
      OK=$((OK + 1))
    fi
  done
done
echo "Downloaded ${OK} files (expected 45 if network allows)."
if [[ "${OK}" -eq 0 ]]; then
  echo "No files downloaded; run: python3 ${ROOT}/generate_synthetic_nnets.py"
fi
