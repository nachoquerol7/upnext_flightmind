#!/usr/bin/env bash
# Lanzador Flightmind: WS_PATH absoluto, sin ~ en .desktop; terminal visible ante errores.
set -euo pipefail

# Ruta absoluta del workspace (testbench/..) — equivalente a cd "$(dirname "$0")/.." && pwd
TBENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_PATH="$(cd "$TBENCH/.." && pwd)"
RUN_SCRIPT="$TBENCH/run_all.sh"
ICON_FILE="$TBENCH/icon.png"

if [[ -d "$HOME/Desktop" ]]; then
  DESKTOP="$(readlink -f "$HOME/Desktop")"
elif [[ -d "$HOME/Escritorio" ]]; then
  DESKTOP="$(readlink -f "$HOME/Escritorio")"
elif [[ -n "${XDG_DESKTOP_DIR:-}" && -d "${XDG_DESKTOP_DIR}" ]]; then
  DESKTOP="$(readlink -f "${XDG_DESKTOP_DIR}")"
else
  mkdir -p "$HOME/Desktop"
  DESKTOP="$(readlink -f "$HOME/Desktop")"
fi

OUT="$DESKTOP/Flightmind_Testbench.desktop"

if [[ ! -f "$ICON_FILE" ]] && command -v python3 >/dev/null 2>&1; then
  python3 "$TBENCH/generate_icon.py"
fi

if [[ ! -f "$ICON_FILE" ]]; then
  echo "ERROR: Falta $ICON_FILE — ejecuta: python3 $TBENCH/generate_icon.py" >&2
  exit 1
fi

ICON_ABS="$(readlink -f "$ICON_FILE")"

chmod +x "$TBENCH/install_launcher.sh" "$RUN_SCRIPT"

# Rutas con espacios: escapado seguro dentro de bash -c "..."
Q_WS="$(printf '%q' "$WS_PATH")"
EXEC_LINE="gnome-terminal -- bash -c \"cd ${Q_WS} && ./testbench/run_all.sh; exec bash\""

{
  echo "[Desktop Entry]"
  echo "Version=1.0"
  echo "Type=Application"
  echo "Name=Flightmind Testbench"
  echo "Comment=SIL: ROS2 Jazzy, rosbridge, proxy LLM, panel web"
  echo "Exec=${EXEC_LINE}"
  echo "Icon=${ICON_ABS}"
  echo "Terminal=false"
  echo "Categories=Development;Science;"
  echo "StartupNotify=true"
} >"$OUT"

chmod +x "$OUT"

if command -v gio >/dev/null 2>&1; then
  gio set "$OUT" metadata::trusted true 2>/dev/null || true
  # GNOME en inglés: ruta explícita pedida para confianza automática
  if [[ -f "$HOME/Desktop/Flightmind_Testbench.desktop" ]]; then
    gio set "$HOME/Desktop/Flightmind_Testbench.desktop" metadata::trusted true 2>/dev/null || true
  fi
fi

echo "Instalado: $OUT"
echo "WS_PATH: $WS_PATH"
echo "Icono: $ICON_ABS"

if command -v notify-send >/dev/null 2>&1; then
  notify-send "Flightmind" "Testbench instalado con éxito en el escritorio" || true
fi
