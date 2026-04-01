from __future__ import annotations

import math

import pytest

from gpp.fl_assignment import M_TO_FT, compute_assigned_fl


def test_tc_fl_001_high_quality_margin_300() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.85, 0.0)
    assert st == "OK"
    assert fl == pytest.approx((1000.0 * M_TO_FT + 300.0) / 100.0, abs=1e-3)


def test_tc_fl_002_degraded_margin_500() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.65, 0.0)
    assert st == "OK"
    assert fl == pytest.approx((1000.0 * M_TO_FT + 500.0) / 100.0, abs=1e-3)


def test_tc_fl_003_quality_08_uses_500ft_margin() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.8, 0.0)
    assert st == "OK"
    assert fl == pytest.approx((1000.0 * M_TO_FT + 500.0) / 100.0, abs=1e-3)


def test_tc_fl_004_quality_05_is_ok() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.5, 0.0)
    assert st == "OK"
    assert math.isfinite(fl)


def test_tc_fl_005_low_quality_hold_nan() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.3, 0.0)
    assert st == "HOLD"
    assert math.isnan(fl)


def test_tc_fl_006_negative_base_margin_is_terrain_invalid() -> None:
    fl, st = compute_assigned_fl(1000.0, 8000.0, 0.9, -500.0)
    assert st == "TERRAIN_INVALID"
    assert math.isnan(fl)


def test_tc_fl_007_no_clamp_when_below_ceiling() -> None:
    fl, st = compute_assigned_fl(100.0, 500.0, 0.9, 0.0)
    assert st == "OK"
    expected = (100.0 * M_TO_FT + 300.0) / 100.0
    assert fl == pytest.approx(expected, abs=1e-3)


def test_tc_fl_008_clamp_when_above_ceiling() -> None:
    fl, st = compute_assigned_fl(5000.0, 2000.0, 0.9, 0.0)
    assert st == "OK"
    assert fl == pytest.approx((2000.0 * M_TO_FT) / 100.0, abs=1e-6)


def test_tc_fl_009_ceiling_zero_invalid() -> None:
    fl, st = compute_assigned_fl(1000.0, 0.0, 0.9, 0.0)
    assert st == "TERRAIN_INVALID"
    assert math.isnan(fl)


def test_tc_fl_010_ceiling_negative_invalid() -> None:
    fl, st = compute_assigned_fl(1000.0, -50.0, 0.9, 0.0)
    assert st == "TERRAIN_INVALID"
    assert math.isnan(fl)


def test_tc_fl_011_terrain_inf_invalid() -> None:
    fl, st = compute_assigned_fl(float("inf"), 8000.0, 0.9, 0.0)
    assert st == "TERRAIN_INVALID"
    assert math.isnan(fl)


def test_tc_fl_012_large_margin_clamps_to_ceiling() -> None:
    fl, st = compute_assigned_fl(1000.0, 1100.0, 0.9, 3000.0)
    assert st == "OK"
    ceiling_fl = (1100.0 * M_TO_FT) / 100.0
    assert fl == pytest.approx(ceiling_fl, abs=1e-6)


def test_tc_fl_013_quality_extremes_are_stable() -> None:
    fl_hi, st_hi = compute_assigned_fl(1000.0, 8000.0, 1.0, 0.0)
    fl_lo, st_lo = compute_assigned_fl(1000.0, 8000.0, 0.0, 0.0)
    assert st_hi == "OK" and math.isfinite(fl_hi)
    assert st_lo == "HOLD" and math.isnan(fl_lo)


