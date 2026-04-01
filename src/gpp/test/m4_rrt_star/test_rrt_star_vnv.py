from __future__ import annotations

import math

import pytest

from gpp.dubins import dubins_interpolate, dubins_length
from gpp.geometry import point_in_polygon
from gpp.rrt_star import RRTStarPlanner


def _path_len(path: list[tuple[float, float, float]]) -> float:
    return sum(math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]) for i in range(len(path) - 1))


def test_tc_rrt_001_no_nfz_path_not_too_long() -> None:
    start, goal = (0.0, 0.0, 0.0), (500.0, 0.0, 0.0)
    pl = RRTStarPlanner(75.0, max_iter=500, seed=42)
    path = pl.plan_if_needed(start, goal, [], (-100.0, 700.0, -200.0, 200.0), [500.0, 0.0, 0.0], "")
    assert _path_len(path) < 1.3 * math.hypot(goal[0] - start[0], goal[1] - start[1])


def test_tc_rrt_002_blocking_nfz_with_low_iter_returns_start_only() -> None:
    block = [(100.0, -200.0), (400.0, -200.0), (400.0, 200.0), (100.0, 200.0)]
    pl = RRTStarPlanner(75.0, max_iter=2, seed=1)
    path = pl.plan_if_needed((0.0, 0.0, 0.0), (500.0, 0.0, 0.0), [block], (-50.0, 550.0, -250.0, 250.0), [500.0, 0.0, 0.0], "b1")
    assert path == [(0.0, 0.0, 0.0)]


def test_tc_rrt_003_path_segments_do_not_enter_nfz() -> None:
    wall = [(140.0, -120.0), (260.0, -120.0), (260.0, 120.0), (140.0, 120.0)]
    pl = RRTStarPlanner(75.0, max_iter=900, seed=9)
    path = pl.plan_if_needed((0.0, 0.0, 0.0), (400.0, 0.0, 0.0), [wall], (-80.0, 500.0, -200.0, 200.0), [400.0, 0.0, 0.0], "w")
    for i in range(len(path) - 1):
        ln, fn = dubins_interpolate(path[i][0], path[i][1], path[i][2], path[i + 1][0], path[i + 1][1], path[i + 1][2], 75.0)
        for k in range(21):
            n, e, _ = fn(ln * k / 20.0)
            assert not point_in_polygon(n, e, wall)


def test_tc_rrt_004_no_replan_same_goal_and_nfz() -> None:
    pl = RRTStarPlanner(75.0, seed=3)
    start, goal = (0.0, 0.0, 0.0), (300.0, 50.0, 0.2)
    b = (-50.0, 400.0, -100.0, 200.0)
    pl.plan_if_needed(start, goal, [], b, [300.0, 50.0, 0.2], "a")
    pl.plan_if_needed(start, goal, [], b, [300.0, 50.0, 0.2], "a")
    assert pl.replan_calls == 1


def test_tc_rrt_005_replan_on_goal_change() -> None:
    pl = RRTStarPlanner(75.0, seed=3)
    b = (-50.0, 500.0, -100.0, 200.0)
    pl.plan_if_needed((0.0, 0.0, 0.0), (300.0, 50.0, 0.2), [], b, [300.0, 50.0, 0.2], "a")
    pl.plan_if_needed((0.0, 0.0, 0.0), (320.0, 50.0, 0.2), [], b, [320.0, 50.0, 0.2], "a")
    assert pl.replan_calls == 2


def test_tc_rrt_006_replan_on_nfz_change() -> None:
    pl = RRTStarPlanner(75.0, seed=3)
    b = (-50.0, 400.0, -100.0, 200.0)
    pl.plan_if_needed((0.0, 0.0, 0.0), (300.0, 50.0, 0.2), [], b, [300.0, 50.0, 0.2], "a")
    pl.plan_if_needed((0.0, 0.0, 0.0), (300.0, 50.0, 0.2), [], b, [300.0, 50.0, 0.2], "b")
    assert pl.replan_calls == 2


def test_tc_rrt_007_all_segments_finite_for_rho_600() -> None:
    pl = RRTStarPlanner(600.0, max_iter=600, seed=2)
    path = pl.plan_if_needed((0.0, 0.0, 0.0), (1400.0, 100.0, 0.1), [], (-100.0, 1500.0, -300.0, 300.0), [1400.0, 100.0, 0.1], "")
    for i in range(len(path) - 1):
        assert math.isfinite(dubins_length(*path[i], *path[i + 1], 600.0))


def test_tc_rrt_008_start_equals_goal_no_exception() -> None:
    pl = RRTStarPlanner(75.0, seed=5)
    path = pl.plan_if_needed((10.0, 20.0, 0.3), (10.0, 20.0, 0.3), [], (0.0, 50.0, 0.0, 50.0), [10.0, 20.0, 0.3], "")
    assert len(path) >= 1


def test_tc_rrt_009_goal_inside_nfz_document_behavior() -> None:
    block = [(200.0, -50.0), (400.0, -50.0), (400.0, 50.0), (200.0, 50.0)]
    pl = RRTStarPlanner(75.0, max_iter=200, seed=6)
    path = pl.plan_if_needed((0.0, 0.0, 0.0), (300.0, 0.0, 0.0), [block], (-100.0, 500.0, -150.0, 150.0), [300.0, 0.0, 0.0], "gi")
    assert len(path) >= 1


def test_tc_rrt_010_deterministic_with_same_seed() -> None:
    args = ((0.0, 0.0, 0.0), (400.0, 10.0, 0.1), [], (-100.0, 500.0, -200.0, 200.0), [400.0, 10.0, 0.1], "")
    p1 = RRTStarPlanner(75.0, seed=42).plan_if_needed(*args)
    p2 = RRTStarPlanner(75.0, seed=42).plan_if_needed(*args)
    assert p1 == p2


def test_tc_rrt_011_goal_nfz_key_changes_with_goal() -> None:
    k1 = RRTStarPlanner.goal_nfz_key([100.0, 0.0, 0.0], "{}")
    k2 = RRTStarPlanner.goal_nfz_key([101.0, 0.0, 0.0], "{}")
    assert k1 != k2


@pytest.mark.xfail(
    reason="GPP-G08: RRT* actual no garantiza monotonía de coste con más iteraciones",
    strict=True,
)
def test_tc_rrt_012_more_iter_not_worse_than_low_iter_same_seed() -> None:
    start, goal = (0.0, 0.0, 0.0), (600.0, 30.0, 0.0)
    b = (-100.0, 700.0, -200.0, 200.0)
    low = RRTStarPlanner(75.0, max_iter=50, seed=7).plan_if_needed(start, goal, [], b, [600.0, 30.0, 0.0], "")
    hi = RRTStarPlanner(75.0, max_iter=500, seed=7).plan_if_needed(start, goal, [], b, [600.0, 30.0, 0.0], "")
    assert _path_len(hi) <= _path_len(low) + 1e-6
