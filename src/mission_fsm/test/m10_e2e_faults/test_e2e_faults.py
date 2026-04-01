"""M10 — E2E fault injection (TC-FAULT-001 … TC-FAULT-012)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_daidalus  # noqa: E402
import mock_fdir  # noqa: E402
import mock_sensors  # noqa: E402


def _reach_cruise(h: SimpleNamespace) -> None:
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    h.inj.inject("takeoff_complete", True)
    assert h.wait_mode("CRUISE")


@pytest.fixture
def faults_runtime(mission_fsm_sil_harness: SimpleNamespace) -> SimpleNamespace:
    ex = mission_fsm_sil_harness.ex
    dai = mock_daidalus.create_mock_daidalus()
    fdir = mock_fdir.create_mock_fdir()
    sens = mock_sensors.create_mock_sensors()
    for n in (dai, fdir, sens):
        ex.add_node(n)
    h = SimpleNamespace(**vars(mission_fsm_sil_harness))
    h.daidalus = dai
    h.fdir = fdir
    h.sensors = sens
    yield h
    for n in (dai, fdir, sens):
        ex.remove_node(n)
        n.destroy_node()


@pytest.mark.xfail(reason="XFAIL-ARCH-1.9: interruption waypoint persistence missing", strict=True)
def test_tc_fault_001_resume_from_saved_waypoint() -> None:
    assert False


def test_tc_fault_002_quality_drop_forces_event(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.inj.inject("quality_flag", 0.1)
    assert faults_runtime.wait_mode("EVENT")


def test_tc_fault_003_daidalus_escalation_forces_event(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.daidalus.inject("alert_level", 2)
    assert faults_runtime.wait_mode("EVENT")


def test_tc_fault_004_fdir_emergency_forces_abort_path(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.inj.inject("abort_command", True)
    assert faults_runtime.wait_mode("RTB")


@pytest.mark.xfail(reason="XFAIL-ARCH-1.6: RTB->ABORT battery cascade transition missing", strict=True)
def test_tc_fault_005_rtb_to_abort_on_battery_cascade() -> None:
    p = Path(__file__).resolve().parents[2] / "config" / "mission_fsm.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    trans = data["fsm"]["transitions"]
    assert any(t["from"] == "RTB" and t["to"] == "ABORT" for t in trans)


def test_tc_fault_006_event_to_abort_on_fdir_emergency(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.inj.inject("quality_flag", 0.1)
    assert faults_runtime.wait_mode("EVENT")
    faults_runtime.inj.inject("fdir_emergency", True)
    assert faults_runtime.spin_until(lambda: "event_to_abort" in faults_runtime.cap.triggers, timeout_sec=5.0)


def test_tc_fault_007_event_to_rtb_command_path(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.inj.inject("quality_flag", 0.1)
    assert faults_runtime.wait_mode("EVENT")
    faults_runtime.inj.inject("rtb_during_event", True)
    assert faults_runtime.wait_mode("RTB")


@pytest.mark.xfail(reason="XFAIL-ARCH-1.7: watchdog node not implemented", strict=True)
def test_tc_fault_008_fdir_drop_detected_by_watchdog() -> None:
    assert False


def test_tc_fault_009_recover_event_to_cruise(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.inj.inject("quality_flag", 0.1)
    assert faults_runtime.wait_mode("EVENT")
    faults_runtime.inj.inject("quality_flag", 1.0)
    faults_runtime.inj.inject("event_cleared", True)
    assert faults_runtime.wait_mode("CRUISE")


def test_tc_fault_010_landing_go_around_reentry(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.inj.inject("land_command", True)
    assert faults_runtime.wait_mode("LANDING")
    faults_runtime.inj.inject("approach_not_stabilized", True)
    assert faults_runtime.wait_mode("GO_AROUND")


def test_tc_fault_011_abort_to_rtb_path(faults_runtime: SimpleNamespace) -> None:
    _reach_cruise(faults_runtime)
    faults_runtime.inj.inject("abort_command", True)
    assert faults_runtime.wait_mode("RTB")


@pytest.mark.xfail(reason="FDIR severity table not implemented", strict=True)
def test_tc_fault_012_fault_severity_cascade_table_exists() -> None:
    assert Path(__file__).resolve().parents[2].joinpath("config", "fdir_severity_table.yaml").exists()
