"""M13 — Átomos de seguridad FSM (TC-ATOM-001..004)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


def _reach_cruise(h: SimpleNamespace) -> None:
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    h.inj.inject("takeoff_complete", True)
    assert h.wait_mode("CRUISE")


def test_tc_atom_001_battery_low_cruise_to_abort(mission_fsm_sil_harness: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("battery_low", True)
    assert mission_fsm_sil_harness.spin_until(
        lambda: "cruise_to_abort" in mission_fsm_sil_harness.cap.triggers, timeout_sec=3.0
    )
    assert mission_fsm_sil_harness.fsm._fsm.state in ("ABORT", "RTB")  # noqa: SLF001 — abort_to_rtb encadena


def test_tc_atom_002_battery_critical_cruise_to_abort(mission_fsm_sil_harness: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("battery_critical", True)
    assert mission_fsm_sil_harness.spin_until(
        lambda: "battery_abort" in mission_fsm_sil_harness.cap.triggers, timeout_sec=3.0
    )


def test_tc_atom_003_c2_lost_cruise_to_rtb(mission_fsm_sil_harness: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("c2_lost", True)
    assert mission_fsm_sil_harness.wait_mode("RTB")
    assert mission_fsm_sil_harness.spin_until(
        lambda: "battery_rtb" in mission_fsm_sil_harness.cap.triggers, timeout_sec=3.0
    )


def test_tc_atom_004_geofence_breach_cruise_to_abort(mission_fsm_sil_harness: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_harness)
    mission_fsm_sil_harness.inj.inject("geofence_breach", True)
    assert mission_fsm_sil_harness.spin_until(
        lambda: "cruise_to_abort" in mission_fsm_sil_harness.cap.triggers, timeout_sec=3.0
    )
    assert mission_fsm_sil_harness.fsm._fsm.state in ("ABORT", "RTB")  # noqa: SLF001
