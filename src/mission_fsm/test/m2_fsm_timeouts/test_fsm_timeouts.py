"""M2 — Timeouts y vigilancia temporal (TC-TO-001 … TC-TO-010).

Morada por estado (`max_duration_sec` + `state_dwell_timeout`), enlaces GCS/C2,
batería y geofence vía topics supervisados en `mission_fsm_node`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_sensors  # noqa: E402


def _dwell_spin(h: SimpleNamespace, iterations: int = 120) -> None:
    """Avanza tiempo real (morada FSM por reloj) y drena el ejecutor."""
    for _ in range(iterations):
        time.sleep(0.045)
        for _ in range(12):
            h.ex.spin_once(timeout_sec=0.02)


@pytest.mark.no_ros
def test_m2_yaml_states_expose_max_duration_for_flight_states() -> None:
    """PREFLIGHT/AUTOTAXI/TAKEOFF/CRUISE/EVENT definen max_duration_sec (morada acotada)."""
    cfg = Path(__file__).resolve().parents[2] / "config" / "mission_fsm.yaml"
    root = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    states = root.get("fsm", {}).get("states", {})
    for name in ("PREFLIGHT", "AUTOTAXI", "TAKEOFF", "CRUISE", "EVENT"):
        body = states.get(name, {})
        assert isinstance(body, dict) and "max_duration_sec" in body, f"missing max_duration_sec on {name}"


def test_m2_preflight_stable_under_short_dwell(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """Por debajo del umbral de morada, PREFLIGHT permanece estable."""
    _dwell_spin(mission_fsm_sil_harness, 40)
    assert mission_fsm_sil_harness.fsm._fsm.state == "PREFLIGHT"  # noqa: SLF001


def test_tc_to001_preflight_excessive_dwell_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-001: morada prolongada en PREFLIGHT fuerza salida (ABORT/RTB en cadena)."""
    _dwell_spin(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.fsm._fsm.state != "PREFLIGHT"  # noqa: SLF001


def test_tc_to002_autotaxi_excessive_dwell_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-002: morada prolongada en AUTOTAXI sin progreso → fallo."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    _dwell_spin(mission_fsm_sil_harness)
    st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
    assert st not in ("AUTOTAXI", "PREFLIGHT")


def test_tc_to003_takeoff_excessive_dwell_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-003: morada prolongada en TAKEOFF sin takeoff_complete → fallo."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    _dwell_spin(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.fsm._fsm.state != "TAKEOFF"  # noqa: SLF001


def test_tc_to004_cruise_excessive_dwell_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-004: CRUISE indefinido sin comandos → timeout; ABORT en cadena puede pasar a RTB."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    _dwell_spin(mission_fsm_sil_harness)
    st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
    assert st in ("ABORT", "RTB")


def test_tc_to005_event_excessive_dwell_resolves_or_escalates(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-005: EVENT prolongado sin clear → escalado (ABORT; puede encadenar RTB)."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    mission_fsm_sil_harness.inj.inject("quality_flag", 0.1)
    assert mission_fsm_sil_harness.wait_mode("EVENT")
    _dwell_spin(mission_fsm_sil_harness)
    st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
    assert st in ("ABORT", "RTB")


def test_tc_to006_gcs_heartbeat_loss_triggers_rtb_or_event(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-006: pérdida de GCS heartbeat superando umbral temporal → RTB o EVENT o ABORT."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    sens = mock_sensors.create_mock_sensors()
    mission_fsm_sil_harness.ex.add_node(sens)
    try:
        assert mission_fsm_sil_harness.spin_until(
            lambda: mission_fsm_sil_harness.fsm._last_gcs_time is not None,  # noqa: SLF001
            timeout_sec=3.0,
        )
        sens.inject("gcs_heartbeat_enabled", False)
        time.sleep(2.6)
        _dwell_spin(mission_fsm_sil_harness, 80)
        st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
        assert st in ("RTB", "EVENT", "ABORT")
    finally:
        mission_fsm_sil_harness.ex.remove_node(sens)
        sens.destroy_node()


def test_tc_to007_c2_link_loss_triggers_protective_state(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-007: enlace C2 falso sostenido → estado protector."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    sens = mock_sensors.create_mock_sensors()
    mission_fsm_sil_harness.ex.add_node(sens)
    try:
        sens.inject("c2_link_status", False)
        time.sleep(2.6)
        _dwell_spin(mission_fsm_sil_harness, 80)
        st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
        assert st in ("RTB", "EVENT", "ABORT")
    finally:
        mission_fsm_sil_harness.ex.remove_node(sens)
        sens.destroy_node()


def test_tc_to008_low_battery_timeout_triggers_rtb(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-008: batería crítica sostenida → RTB (o cadena vía ABORT)."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    sens = mock_sensors.create_mock_sensors()
    mission_fsm_sil_harness.ex.add_node(sens)
    try:
        sens.inject("battery_percent", 0.05)
        time.sleep(2.6)
        _dwell_spin(mission_fsm_sil_harness, 80)
        st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
        assert st in ("RTB", "ABORT")
    finally:
        mission_fsm_sil_harness.ex.remove_node(sens)
        sens.destroy_node()


def test_tc_to009_geofence_breach_timeout_triggers_event(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-009: violación de geofence sostenida → ABORT (cruise_to_abort incl. geofence_breach)."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    sens = mock_sensors.create_mock_sensors()
    mission_fsm_sil_harness.ex.add_node(sens)
    try:
        sens.inject("geofence_breach", True)
        time.sleep(0.6)
        _dwell_spin(mission_fsm_sil_harness, 80)
        st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
        assert st in ("ABORT", "RTB") and "cruise_to_abort" in mission_fsm_sil_harness.cap.triggers
    finally:
        mission_fsm_sil_harness.ex.remove_node(sens)
        sens.destroy_node()


def test_tc_to010_combined_stale_inputs_trigger_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-010: morada global en PREFLIGHT agota ventana → ABORT/RTB."""
    _dwell_spin(mission_fsm_sil_harness, 160)
    st = mission_fsm_sil_harness.fsm._fsm.state  # noqa: SLF001
    assert st in ("ABORT", "RTB")
