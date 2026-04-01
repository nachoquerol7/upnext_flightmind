"""FL assignment tests."""

from __future__ import annotations

import math

from gpp.fl_assignment import M_TO_FT, compute_assigned_fl


def test_fl_nominal() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.9, 50.0)
    assert st == "OK"
    assert math.isfinite(fl)
    assert fl > 0.0


def test_fl_degraded_uses_larger_margin_than_high_quality() -> None:
    _, st = compute_assigned_fl(1000.0, 8000.0, 0.6, 0.0)
    assert st == "OK"
    fl_hi, _ = compute_assigned_fl(1000.0, 8000.0, 0.85, 0.0)
    fl_lo, _ = compute_assigned_fl(1000.0, 8000.0, 0.6, 0.0)
    assert fl_lo > fl_hi


def test_fl_ceiling_clamp() -> None:
    ceiling_m = 2000.0
    fl, st = compute_assigned_fl(5000.0, ceiling_m, 0.95, 0.0)
    assert st == "OK"
    max_fl = (ceiling_m * M_TO_FT) / 100.0
    assert fl <= max_fl + 1e-6


def test_fl_nan_terrain() -> None:
    fl, st = compute_assigned_fl(float("nan"), 5000.0, 0.9, 0.0)
    assert st == "TERRAIN_INVALID"
    assert math.isnan(fl)


def test_fl_hold_low_quality() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.4, 0.0)
    assert st == "HOLD"
    assert math.isnan(fl)
