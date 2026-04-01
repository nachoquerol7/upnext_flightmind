"""M2 — Timeouts y vigilancia temporal (TC-TO-001 … TC-TO-010)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_sensors  # noqa: E402


def _dwell_spin(h: SimpleNamespace, iterations: int = 120) -> None:
    for _ in range(iterations):
        h.ex.spin_once(timeout_sec=0.05)


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.2: sin max_duration_sec en estados ni temporizador de morada en mission_fsm_node",
    strict=True,
)
def test_tc_to001_preflight_excessive_dwell_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-001: morada prolongada en PREFLIGHT debe forzar salida a estado de fallo."""
    _dwell_spin(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.cap.mode != "PREFLIGHT"


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.2: sin max_duration_sec en estados ni temporizador de morada en mission_fsm_node",
    strict=True,
)
def test_tc_to002_autotaxi_excessive_dwell_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-002: morada prolongada en AUTOTAXI sin progreso → fallo."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    _dwell_spin(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.cap.mode not in ("AUTOTAXI", "PREFLIGHT")


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.2: sin max_duration_sec en estados ni temporizador de morada en mission_fsm_node",
    strict=True,
)
def test_tc_to003_takeoff_excessive_dwell_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-003: morada prolongada en TAKEOFF sin takeoff_complete → fallo."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    _dwell_spin(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.cap.mode != "TAKEOFF"


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.2: sin max_duration_sec en estados ni temporizador de morada en mission_fsm_node",
    strict=True,
)
def test_tc_to004_cruise_excessive_dwell_without_command_moves_to_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-004: CRUISE indefinido sin nuevos comandos → timeout de misión."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    _dwell_spin(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.cap.mode == "ABORT"


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.2: sin max_duration_sec en estados ni temporizador de morada en mission_fsm_node",
    strict=True,
)
def test_tc_to005_event_excessive_dwell_resolves_or_escalates(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-005: EVENT prolongado sin clear → escalado automático."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    mission_fsm_sil_harness.inj.inject("quality_flag", 0.1)
    assert mission_fsm_sil_harness.wait_mode("EVENT")
    _dwell_spin(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.cap.mode == "ABORT"


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.7: mission_fsm no integra timeout por pérdida de GCS heartbeat",
    strict=True,
)
def test_tc_to006_gcs_heartbeat_loss_triggers_rtb_or_event(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-006: pérdida de GCS heartbeat superando umbral temporal → RTB o EVENT."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    sens = mock_sensors.create_mock_sensors()
    mission_fsm_sil_harness.ex.add_node(sens)
    try:
        _dwell_spin(mission_fsm_sil_harness, 80)
        assert mission_fsm_sil_harness.cap.mode in ("RTB", "EVENT", "ABORT")
    finally:
        mission_fsm_sil_harness.ex.remove_node(sens)
        sens.destroy_node()


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.7: mission_fsm no integra timeout por enlace C2",
    strict=True,
)
def test_tc_to007_c2_link_loss_triggers_protective_state(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-007: c2_link_status falso sostenido → estado protector."""
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
        _dwell_spin(mission_fsm_sil_harness, 80)
        assert mission_fsm_sil_harness.cap.mode in ("RTB", "EVENT", "ABORT")
    finally:
        mission_fsm_sil_harness.ex.remove_node(sens)
        sens.destroy_node()


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.7: mission_fsm no reacciona a batería baja con transición temporal",
    strict=True,
)
def test_tc_to008_low_battery_timeout_triggers_rtb(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-008: batería crítica sostenida → RTB u aborto temporal."""
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
        _dwell_spin(mission_fsm_sil_harness, 80)
        assert mission_fsm_sil_harness.cap.mode == "RTB"
    finally:
        mission_fsm_sil_harness.ex.remove_node(sens)
        sens.destroy_node()


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.7: sin vigilancia de geofence con temporizador previo al FSM",
    strict=True,
)
def test_tc_to009_geofence_breach_timeout_triggers_event(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-009: violación de geofence sostenida → EVENT."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF")
    mission_fsm_sil_harness.inj.inject("takeoff_complete", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    _dwell_spin(mission_fsm_sil_harness, 80)
    assert mission_fsm_sil_harness.cap.mode == "EVENT"


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.2: sin temporización combinada de misión; ver también ARCH-1.7",
    strict=True,
)
def test_tc_to010_combined_stale_inputs_trigger_fault(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-TO-010: entradas estancadas (sin tick de progreso) agotan ventana global."""
    _dwell_spin(mission_fsm_sil_harness, 160)
    assert mission_fsm_sil_harness.cap.mode == "ABORT"
