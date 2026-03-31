#!/usr/bin/env bash
# Descarga opcional de GeoJSON público (ejemplo). Sustituye la URL por tu fuente (licencia OK).
set -euo pipefail
OUT="${1:-$(dirname "$0")/../src/upnext_airspace/config/downloaded.geojson}"
echo "Guardando en: $OUT"
echo "Edita este script con una URL válida (p. ej. datos abiertos con licencia permitida)."
# curl -fsSL "https://example.com/airspace.geojson" -o "$OUT"
