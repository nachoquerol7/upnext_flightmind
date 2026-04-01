"""Takeoff manager tests."""

from __future__ import annotations

from gpp.takeoff_manager import TakeoffConfig, TakeoffManager


def test_takeoff_nominal_sequence() -> None:
    cfg = TakeoffConfig(cruise_alt_agl_m=100.0, vr_mps=28.0)
    m = TakeoffManager(cfg)
    assert m.update(0.0, 2500.0, 0.0, 0.0) == "GROUND"
    assert m.update(25.0, 2500.0, 0.0, 0.0) == "GROUND"
    assert m.update(27.0, 2500.0, 0.0, 0.0) == "ROTATE"
    assert m.update(30.0, 2400.0, 6.0, 0.0) == "CLIMB"
    assert m.update(45.0, 5000.0, 80.0, 3.0, desired_climb_mps=6.0) == "CLIMB"
    assert m.update(50.0, 5000.0, 105.0, 2.0, desired_climb_mps=6.0) == "CRUISE"


def test_takeoff_abort_short_runway() -> None:
    m = TakeoffManager(TakeoffConfig())
    m.update(10.0, 8.0, 0.0, 0.0)
    assert m.phase == "ABORT"


def test_takeoff_climb_respects_vehicle_model_max() -> None:
    cfg = TakeoffConfig(climb_rate_max_mps=8.0, cruise_alt_agl_m=500.0, vr_mps=28.0)
    m = TakeoffManager(cfg)
    m.update(25.0, 3000.0, 0.0, 0.0)
    m.update(27.0, 3000.0, 0.0, 0.0)
    m.update(27.0, 3000.0, 6.0, 0.0)
    assert m.phase == "CLIMB"
    m.update(40.0, 3000.0, 30.0, 2.0, desired_climb_mps=25.0)
    assert m.commanded_climb_mps <= cfg.climb_rate_max_mps + 1e-9
    assert m.commanded_climb_mps == 8.0
