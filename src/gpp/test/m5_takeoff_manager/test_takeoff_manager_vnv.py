from __future__ import annotations

import math

from gpp.takeoff_manager import TakeoffConfig, TakeoffManager


def test_tc_to_001_nominal_sequence_to_cruise() -> None:
    m = TakeoffManager(TakeoffConfig(cruise_alt_agl_m=100.0, vr_mps=28.0))
    assert m.update(27.0, 3000.0, 0.0, 0.0) == "ROTATE"
    assert m.update(30.0, 2800.0, 5.0, 0.0) == "CLIMB"
    assert m.update(40.0, 2500.0, 120.0, 3.0, desired_climb_mps=6.0) == "CRUISE"
    assert m.commanded_climb_mps == 0.0


def test_tc_to_002_abort_boundary_at_79_and_not_80() -> None:
    m = TakeoffManager(TakeoffConfig(decel_mps2=2.5))
    assert m.update(20.0, 79.0, 0.0, 0.0) == "ABORT"
    m.reset()
    assert m.update(20.0, 80.0, 0.0, 0.0) != "ABORT"


def test_tc_to_003_abort_in_rotate_when_runway_insufficient() -> None:
    m = TakeoffManager(TakeoffConfig(vr_mps=28.0, decel_mps2=2.5))
    m.update(27.0, 3000.0, 0.0, 0.0)
    assert m.phase == "ROTATE"
    assert m.update(25.0, 50.0, 0.0, 0.0) == "ABORT"


def test_tc_to_004_no_abort_in_climb_due_to_runway() -> None:
    m = TakeoffManager(TakeoffConfig(vr_mps=28.0))
    m.update(27.0, 3000.0, 0.0, 0.0)
    m.update(30.0, 3000.0, 5.0, 0.0)
    assert m.phase == "CLIMB"
    assert m.update(40.0, 0.0, 10.0, 2.0, desired_climb_mps=3.0) == "CLIMB"


def test_tc_to_005_abort_is_terminal_until_reset() -> None:
    m = TakeoffManager()
    m.update(20.0, 10.0, 0.0, 0.0)
    assert m.phase == "ABORT"
    for _ in range(3):
        assert m.update(50.0, 4000.0, 200.0, 5.0, desired_climb_mps=6.0) == "ABORT"


def test_tc_to_006_reset_resets_phase_and_command() -> None:
    m = TakeoffManager()
    m.update(20.0, 10.0, 0.0, 0.0)
    m.reset()
    assert m.phase == "GROUND"
    assert m.commanded_climb_mps == 0.0


def test_tc_to_007_climb_command_clamped_to_max() -> None:
    m = TakeoffManager(TakeoffConfig(climb_rate_max_mps=8.0, vr_mps=28.0, cruise_alt_agl_m=200.0))
    m.update(27.0, 3000.0, 0.0, 0.0)
    m.update(30.0, 3000.0, 5.0, 0.0)
    m.update(40.0, 3000.0, 30.0, 1.0, desired_climb_mps=100.0)
    assert m.commanded_climb_mps == 8.0


def test_tc_to_008_command_zero_in_cruise() -> None:
    m = TakeoffManager(TakeoffConfig(cruise_alt_agl_m=30.0))
    m.update(27.0, 3000.0, 0.0, 0.0)
    m.update(30.0, 3000.0, 5.0, 0.0)
    m.update(40.0, 3000.0, 40.0, 2.0, desired_climb_mps=3.0)
    assert m.phase == "CRUISE"
    assert m.commanded_climb_mps == 0.0


def test_tc_to_009_braking_distance_nominal() -> None:
    assert TakeoffManager.braking_distance_m(20.0, 2.5) == 80.0


def test_tc_to_010_braking_distance_zero_decel_finite_large() -> None:
    bd = TakeoffManager.braking_distance_m(20.0, 0.0)
    assert math.isfinite(bd)
    assert bd > 1e6


def test_tc_to_011_rotate_to_climb_on_exact_liftoff_alt() -> None:
    m = TakeoffManager(TakeoffConfig(liftoff_alt_m=5.0))
    m.update(27.0, 3000.0, 0.0, 0.0)
    assert m.update(30.0, 3000.0, 5.0, 0.0) == "CLIMB"


def test_tc_to_012_ground_to_rotate_on_exact_threshold() -> None:
    cfg = TakeoffConfig(vr_mps=28.0, rotate_threshold=0.95)
    m = TakeoffManager(cfg)
    assert m.update(28.0 * 0.95, 3000.0, 0.0, 0.0) == "ROTATE"
