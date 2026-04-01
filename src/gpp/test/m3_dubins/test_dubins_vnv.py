from __future__ import annotations

import math

import pytest

from gpp.dubins import dubins_interpolate, dubins_length
from gpp.rrt_star import RRTStarPlanner


def test_tc_dub_001_straight_line_length() -> None:
    L = dubins_length(0.0, 0.0, 0.0, 1000.0, 0.0, 0.0, 600.0)
    assert abs(L - 1000.0) <= 5.0


def test_tc_dub_002_turn_90_is_finite_and_ge_euclidean() -> None:
    L = dubins_length(0.0, 0.0, 0.0, 500.0, 500.0, math.pi / 2.0, 600.0)
    assert math.isfinite(L)
    assert L >= math.hypot(500.0, 500.0)


@pytest.mark.xfail(
    reason="GPP-G07: dubins_length no garantiza ~0 para start==goal en todos los headings",
    strict=True,
)
def test_tc_dub_003_start_equals_goal_near_zero() -> None:
    L = dubins_length(10.0, 20.0, 0.3, 10.0, 20.0, 0.3, 600.0)
    assert L <= 1e-6


def test_tc_dub_004_zero_rho_returns_inf_and_safe_interpolator() -> None:
    L = dubins_length(0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0)
    Li, fn = dubins_interpolate(0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0)
    assert math.isinf(L)
    assert math.isinf(Li)
    assert fn(10.0) == (0.0, 0.0, 0.0)


def test_tc_dub_005_tiny_rho_below_threshold_is_inf() -> None:
    assert math.isinf(dubins_length(0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 1e-10))


def test_tc_dub_006_interpolate_at_zero_is_start() -> None:
    _, fn = dubins_interpolate(1.0, 2.0, 0.25, 100.0, 40.0, 0.7, 600.0)
    n, e, h = fn(0.0)
    assert abs(n - 1.0) <= 1e-6 and abs(e - 2.0) <= 1e-6 and abs(h - 0.25) <= 1e-6


def test_tc_dub_007_interpolate_at_length_is_goal() -> None:
    L, fn = dubins_interpolate(0.0, 0.0, 0.0, 500.0, 50.0, 0.2, 600.0)
    n, e, h = fn(L)
    assert abs(n - 500.0) <= 1.0 and abs(e - 50.0) <= 1.0 and abs(h - 0.2) <= 1e-4


def test_tc_dub_008_interpolate_after_length_clamps_to_end() -> None:
    L, fn = dubins_interpolate(0.0, 0.0, 0.0, 200.0, -40.0, -0.2, 600.0)
    p1 = fn(L)
    p2 = fn(L + 1000.0)
    assert p1 == p2


def test_tc_dub_009_u_turn_length_lower_bound() -> None:
    L = dubins_length(0.0, 0.0, 0.0, 0.0, 0.0, math.pi, 600.0)
    assert L >= math.pi * 600.0


def test_tc_dub_010_headings_outside_pi_range_are_handled() -> None:
    L = dubins_length(0.0, 0.0, 5.0, 600.0, 0.0, -5.0, 600.0)
    assert math.isfinite(L)


def test_tc_dub_011_rrt_segments_have_finite_dubins_length() -> None:
    planner = RRTStarPlanner(600.0, max_iter=400, seed=42)
    path = planner.plan_if_needed((0.0, 0.0, 0.0), (1000.0, 100.0, 0.1), [], (-100.0, 1200.0, -300.0, 300.0), [1000.0, 100.0, 0.1], "")
    for i in range(len(path) - 1):
        L = dubins_length(path[i][0], path[i][1], path[i][2], path[i + 1][0], path[i + 1][1], path[i + 1][2], 600.0)
        assert math.isfinite(L)
