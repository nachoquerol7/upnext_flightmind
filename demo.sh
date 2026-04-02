#!/usr/bin/env bash
# Flightmind / UpNext — arranque único demo (terminal única, remoto).

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WS" || exit 1

# --- Entorno ROS (stderr suprimido: evita ruido "not found:" de underlays) ---
# Nota: `set -u` no debe activarse antes de los setup.bash (rompen con vars opcionales).
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash 2>/dev/null || true
# shellcheck disable=SC1091
source "${HOME}/archive_repos/ros2_ws/src/install/setup.bash" 2>/dev/null || true
# shellcheck disable=SC1091
source "${WS}/install/setup.bash" 2>/dev/null || true

set -u

# --- ANSI ---
C_GRN='\033[0;32m'
C_RED='\033[0;31m'
C_YEL='\033[1;33m'
C_DIM='\033[2m'
C_RST='\033[0m'

print_banner() {
  echo ""
  echo "╔══════════════════════════════════════╗"
  echo "║   Flightmind Autonomy Stack — Demo   ║"
  echo "║   UpNext / Airbus UpNext  2026-04-01 ║"
  echo "╚══════════════════════════════════════╝"
  echo ""
}

# Última línea de resumen pytest en un log colcon test (stdout_stderr.log).
parse_pytest_summary_line() {
  local logf="$1"
  [[ -f "$logf" ]] || return 1
  grep -E '=+[[:space:]]*[0-9]+[[:space:]]+passed' "$logf" 2>/dev/null | tail -1
}

extract_count() {
  local label="$2"
  local line="$1"
  # shellcheck disable=SC2001
  echo "$line" | sed -n "s/.*\b\([0-9][0-9]*\) ${label}\b.*/\1/p" | head -1
}

# Busca log de test colcon para un paquete (latest_test, si no, test_* más reciente).
find_test_stdout_stderr() {
  local pkg_dir="$1"
  local root="${WS}/log"
  local f

  if [[ -L "${root}/latest_test" || -d "${root}/latest_test" ]]; then
    f="${root}/latest_test/${pkg_dir}/stdout_stderr.log"
    [[ -f "$f" ]] && { echo "$f"; return 0; }
  fi

  local d
  while IFS= read -r d; do
    f="${d}/${pkg_dir}/stdout_stderr.log"
    [[ -f "$f" ]] && { echo "$f"; return 0; }
  done < <(ls -1td "${root}"/test_* 2>/dev/null)
  return 1
}

print_suite_line() {
  local display_name="$1"
  local pkg_dir="$2"
  local logf
  local line passed failed xfailed errors

  if ! logf="$(find_test_stdout_stderr "$pkg_dir")"; then
    echo -e "${C_YEL}[SUITE]${C_RST} ${display_name} ${C_YEL}(sin log colcon test reciente para este paquete)${C_RST}"
    return
  fi

  line="$(parse_pytest_summary_line "$logf")"
  if [[ -z "$line" ]]; then
    echo -e "${C_YEL}[SUITE]${C_RST} ${display_name} ${C_YEL}(log sin resumen pytest)${C_RST}"
    return
  fi

  passed="$(extract_count "$line" passed)"
  failed="$(extract_count "$line" failed)"
  xfailed="$(extract_count "$line" xfailed)"
  errors="$(extract_count "$line" errors)"
  [[ -n "$passed" ]] || passed=0
  [[ -n "$failed" ]] || failed=0
  [[ -n "$xfailed" ]] || xfailed=0
  [[ -n "$errors" ]] || errors=0
  failed=$((failed + errors))

  local p_txt f_txt x_txt
  p_txt="${C_GRN}${passed} passed${C_RST}"
  if [[ "$xfailed" -gt 0 ]]; then
    x_txt="${C_YEL}${xfailed} xfailed${C_RST}"
  else
    x_txt="${C_GRN}${xfailed} xfailed${C_RST}"
  fi
  if [[ "$failed" -gt 0 ]]; then
    f_txt="${C_RED}${failed} failed${C_RST}"
  else
    f_txt="${C_GRN}${failed} failed${C_RST}"
  fi

  printf '%b\n' "${C_DIM}[SUITE]${C_RST} ${display_name} ${p_txt} · ${x_txt} · ${f_txt}"
}

print_test_summaries() {
  echo -e "${C_DIM}Resumen del último colcon test (log/latest_test y, si aplica, test_* previos):${C_RST}"
  print_suite_line "mission_fsm:" "mission_fsm"
  print_suite_line "gpp:         " "gpp"
  print_suite_line "fdir:        " "fdir"
  print_suite_line "acas_node:   " "acas_node"
  print_suite_line "nav_bridge:  " "navigation_bridge"
  echo ""
}

show_menu() {
  echo "Selecciona demo:"
  echo "  [1] Suite demo FSM (6 tests · ~6s)"
  echo "  [2] T1 GPP NFZ Avoidance standalone"
  echo "  [3] Ejecutar ambos"
  echo "  [q] Salir"
  echo ""
  printf 'Opción: '
}

run_fsm_demo() {
  echo -e "\n${C_DIM}--- Suite demo FSM ---${C_RST}\n"
  (
    cd "${WS}/src/mission_fsm" || exit 1
    python3 -m pytest -c pytest_demo.ini -m demo -v --timeout=30
  )
  local ec=$?
  if [[ "$ec" -eq 0 ]]; then
    echo -e "\n${C_GRN}FSM demo: PASS${C_RST}\n"
  else
    echo -e "\n${C_RED}FSM demo: FAIL (exit ${ec})${C_RST}\n"
  fi
  return "$ec"
}

run_gpp_demo() {
  echo -e "\n${C_DIM}--- T1 GPP NFZ ---${C_RST}\n"
  (cd "$WS" && python3 src/gpp/test/demo/test_demo_t1_gpp_nfz.py)
  local ec=$?
  if [[ "$ec" -eq 0 ]]; then
    echo -e "\n${C_GRN}GPP T1: PASS${C_RST}\n"
  else
    echo -e "\n${C_RED}GPP T1: FAIL (exit ${ec})${C_RST}\n"
  fi
  return "$ec"
}

# --- main ---
print_banner
print_test_summaries

while true; do
  show_menu
  read -r choice || exit 0
  case "${choice,,}" in
    q|quit|exit|"")
      echo -e "${C_YEL}Salida.${C_RST}"
      exit 0
      ;;
    1)
      run_fsm_demo || true
      ;;
    2)
      run_gpp_demo || true
      ;;
    3)
      ok=0
      run_fsm_demo || ok=1
      run_gpp_demo || ok=1
      if [[ "$ok" -eq 0 ]]; then
        echo -e "${C_GRN}Ambos: PASS${C_RST}"
      else
        echo -e "${C_RED}Ambos: al menos uno FAIL${C_RST}"
      fi
      ;;
    *)
      echo -e "${C_YEL}Opción no válida.${C_RST}\n"
      ;;
  esac
done
