"""M1 — Transiciones FSM vía ROS 2 (TC-FSM-001 … TC-FSM-024)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_daidalus  # noqa: E402
import mock_fastlio2  # noqa: E402


def _reach_cruise(h: SimpleNamespace) -> None:
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    h.inj.inject("takeoff_complete", True)
    assert h.wait_mode("CRUISE")


def _reach_landing(h: SimpleNamespace) -> None:
    _reach_cruise(h)
    h.inj.inject("land_command", True)
    assert h.wait_mode("LANDING")


def _reach_event_via_quality(h: SimpleNamespace) -> None:
    _reach_cruise(h)
    h.inj.inject("quality_flag", 0.1)
    assert h.wait_mode("EVENT")


def _drain_executor(h: SimpleNamespace, iterations: int = 120) -> None:
    """Vacía mensajes pendientes para que el capture reciba todos los active_trigger."""
    for _ in range(iterations):
        h.ex.spin_once(timeout_sec=0.02)


@pytest.fixture
def mission_fsm_sil_with_fastlio(mission_fsm_sil_harness: SimpleNamespace) -> SimpleNamespace:
    """Harness + mock FastLIO2 (mismo executor)."""
    lio = mock_fastlio2.create_mock_fastlio2()
    mission_fsm_sil_harness.ex.add_node(lio)
    h = SimpleNamespace(**vars(mission_fsm_sil_harness))
    h.fastlio = lio
    yield h
    mission_fsm_sil_harness.ex.remove_node(lio)
    lio.destroy_node()


@pytest.fixture
def mission_fsm_sil_with_daidalus(mission_fsm_sil_harness: SimpleNamespace) -> SimpleNamespace:
    dai = mock_daidalus.create_mock_daidalus()
    mission_fsm_sil_harness.ex.add_node(dai)
    h = SimpleNamespace(**vars(mission_fsm_sil_harness))
    h.daidalus = dai
    yield h
    mission_fsm_sil_harness.ex.remove_node(dai)
    dai.destroy_node()


def test_tc_fsm_001_preflight_to_autotaxi(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-001: preflight_ok dispara PREFLIGHT→AUTOTAXI (to_autotaxi)."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI") and "to_autotaxi" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_002_autotaxi_to_takeoff(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-002: taxi_clear en AUTOTAXI dispara to_takeoff."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    mission_fsm_sil_harness.inj.inject("taxi_clear", True)
    assert mission_fsm_sil_harness.wait_mode("TAKEOFF") and "to_takeoff" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_003_takeoff_to_cruise(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-003: takeoff_complete dispara TAKEOFF→CRUISE."""
    _reach_cruise(mission_fsm_sil_harness)
    assert mission_fsm_sil_harness.cap.mode == "CRUISE" and "to_cruise" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_004_cruise_to_event_quality_via_fastlio(mission_fsm_sil_with_fastlio: SimpleNamespace) -> None:
    """TC-FSM-004: calidad por debajo del umbral vía mock FastLIO2 → EVENT."""
    _reach_cruise(mission_fsm_sil_with_fastlio)
    mission_fsm_sil_with_fastlio.fastlio.inject("quality_flag", 0.1)
    assert mission_fsm_sil_with_fastlio.wait_mode("EVENT") and "to_event" in mission_fsm_sil_with_fastlio.cap.triggers


def test_tc_fsm_005_cruise_to_event_daidalus_via_mock(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    """TC-FSM-005: alerta DAIDALUS ≥ ámbar vía mock → EVENT."""
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 2)
    assert mission_fsm_sil_with_daidalus.wait_mode("EVENT") and "to_event" in mission_fsm_sil_with_daidalus.cap.triggers


def test_tc_fsm_006_cruise_to_rtb(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-006: rtb_command → RTB."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("rtb_command", True)
    assert mission_fsm_sil_harness.wait_mode("RTB") and "cruise_to_rtb" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_007_cruise_to_landing(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-007: land_command → LANDING."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("land_command", True)
    assert mission_fsm_sil_harness.wait_mode("LANDING")
    _drain_executor(mission_fsm_sil_harness)
    assert "to_landing" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_008_event_to_cruise(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-008: event_cleared con entradas saneadas → CRUISE."""
    _reach_event_via_quality(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("quality_flag", 1.0)
    mission_fsm_sil_harness.inj.inject("event_cleared", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE") and "event_to_cruise" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_009_event_to_abort(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-009: fdir_emergency en EVENT → ABORT."""
    _reach_event_via_quality(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("fdir_emergency", True)
    assert mission_fsm_sil_harness.spin_until(
        lambda: "event_to_abort" in mission_fsm_sil_harness.cap.triggers, timeout_sec=5.0
    )


def test_tc_fsm_010_cruise_abort_direct_does_not_use_to_event(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-010: abort en CRUISE con calidad nominal no pasa por to_event."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("abort_command", True)
    assert mission_fsm_sil_harness.spin_until(
        lambda: "cruise_to_abort" in mission_fsm_sil_harness.cap.triggers, timeout_sec=5.0
    ) and ("to_event" not in mission_fsm_sil_harness.cap.triggers)


def test_tc_fsm_011_event_to_rtb(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-011: rtb_during_event → RTB."""
    _reach_event_via_quality(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("rtb_during_event", True)
    assert mission_fsm_sil_harness.wait_mode("RTB")
    assert mission_fsm_sil_harness.spin_until(
        lambda: "event_to_rtb" in mission_fsm_sil_harness.cap.triggers, timeout_sec=5.0
    )


def test_tc_fsm_012_landing_to_go_around(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-012: approach_not_stabilized en LANDING → GO_AROUND."""
    _reach_landing(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("approach_not_stabilized", True)
    assert mission_fsm_sil_harness.wait_mode("GO_AROUND")
    assert mission_fsm_sil_harness.spin_until(
        lambda: "landing_to_goaround" in mission_fsm_sil_harness.cap.triggers, timeout_sec=5.0
    )


def test_tc_fsm_013_landing_to_autotaxi_touchdown(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-013: touchdown → AUTOTAXI (landing_complete)."""
    _reach_landing(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("touchdown", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI") and "landing_complete" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_014_go_around_to_landing(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-014: go_around_complete → LANDING."""
    _reach_landing(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("approach_not_stabilized", True)
    assert mission_fsm_sil_harness.wait_mode("GO_AROUND")
    mission_fsm_sil_harness.inj.inject("go_around_complete", True)
    assert mission_fsm_sil_harness.wait_mode("LANDING") and "goaround_to_landing" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_015_go_around_to_cruise(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-015: missed_approach_climb → CRUISE."""
    _reach_landing(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("approach_not_stabilized", True)
    assert mission_fsm_sil_harness.wait_mode("GO_AROUND")
    mission_fsm_sil_harness.inj.inject("missed_approach_climb", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE")
    _drain_executor(mission_fsm_sil_harness)
    assert "goaround_to_cruise" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_016_abort_to_rtb(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-016: desde ABORT la transición vacía dispara abort_to_rtb (observado en RTB)."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("abort_command", True)
    tr = mission_fsm_sil_harness.cap.triggers
    assert mission_fsm_sil_harness.wait_mode("RTB") and "cruise_to_abort" in tr and "abort_to_rtb" in tr


def test_tc_fsm_017_rtb_to_landing(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-017: rtb_landing → LANDING."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("rtb_command", True)
    assert mission_fsm_sil_harness.wait_mode("RTB")
    mission_fsm_sil_harness.inj.inject("rtb_landing", True)
    assert mission_fsm_sil_harness.wait_mode("LANDING")
    _drain_executor(mission_fsm_sil_harness)
    assert "rtb_to_landing" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_018_rtb_to_cruise(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-018: rtb_cancel → CRUISE."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("rtb_command", True)
    assert mission_fsm_sil_harness.wait_mode("RTB")
    mission_fsm_sil_harness.inj.inject("rtb_cancel", True)
    assert mission_fsm_sil_harness.wait_mode("CRUISE") and "rtb_to_cruise" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_019_cruise_abort_wins_over_event_path(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-019: abort_command y calidad mala: primera coincidencia es cruise_to_abort, no to_event."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("quality_flag", 0.1)
    mission_fsm_sil_harness.inj.inject("abort_command", True)
    assert mission_fsm_sil_harness.spin_until(
        lambda: "cruise_to_abort" in mission_fsm_sil_harness.cap.triggers, timeout_sec=5.0
    ) and ("to_event" not in mission_fsm_sil_harness.cap.triggers)


def test_tc_fsm_020_cruise_rtb_before_landing_when_both_commands(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-020: rtb_command y land_command: orden YAML favorece cruise_to_rtb."""
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("land_command", True)
    mission_fsm_sil_harness.inj.inject("rtb_command", True)
    assert mission_fsm_sil_harness.wait_mode("RTB") and "cruise_to_rtb" in mission_fsm_sil_harness.cap.triggers


def test_tc_fsm_021_preflight_holds_without_preflight_ok(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-021: sin preflight_ok permanece en PREFLIGHT."""
    for _ in range(60):
        mission_fsm_sil_harness.ex.spin_once(timeout_sec=0.05)
    assert mission_fsm_sil_harness.fsm._fsm.state == "PREFLIGHT"  # noqa: SLF001 — cap.mode puede rezagarse con QoS volatile


def test_tc_fsm_022_autotaxi_holds_without_taxi_clear(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-022: en AUTOTAXI sin taxi_clear no avanza a TAKEOFF."""
    mission_fsm_sil_harness.inj.inject("preflight_ok", True)
    assert mission_fsm_sil_harness.wait_mode("AUTOTAXI")
    for _ in range(60):
        mission_fsm_sil_harness.ex.spin_once(timeout_sec=0.05)
    assert mission_fsm_sil_harness.fsm._fsm.state == "AUTOTAXI"  # noqa: SLF001


@pytest.mark.xfail(reason="XFAIL-ARCH-1.1: sin parámetro ni lógica de histéresis temporal en quality_flag", strict=True)
def test_tc_fsm_023_quality_hysteresis_declared_on_node(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-023: el nodo expone histéresis de calidad (p. ej. quality_flag_hysteresis_sec)."""
    names = mission_fsm_sil_harness.fsm.get_parameter_names()
    assert any("hysteresis" in n for n in names)


@pytest.mark.xfail(reason="XFAIL-ARCH-1.3: sin substates de EVENT expuestos en /fsm", strict=True)
def test_tc_fsm_024_event_substate_suffix_in_current_mode(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-FSM-024: modo publicado refleja subestado de EVENT (p. ej. EVENT:AVOID)."""
    _reach_event_via_quality(mission_fsm_sil_harness)
    assert ":" in mission_fsm_sil_harness.cap.mode
