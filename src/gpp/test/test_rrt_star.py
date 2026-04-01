"""Informed RRT* + Dubins tests."""

from __future__ import annotations

import json

from gpp.dubins import dubins_interpolate
from gpp.geometry import point_in_polygon
from gpp.rrt_star import RRTStarPlanner, _dubins_collision


def test_rrt_simple_path_no_nfz() -> None:
    start = (0.0, 0.0, 0.0)
    goal = (350.0, 0.0, 0.0)
    bounds = (-80.0, 450.0, -200.0, 200.0)
    pl = RRTStarPlanner(75.0, seed=7)
    path = pl.plan_if_needed(start, goal, [], bounds, [350.0, 0.0, 0.0], "")
    assert len(path) >= 2
    assert path[-1] == goal
    assert pl.replan_calls == 1


def test_rrt_path_avoids_nfz() -> None:
    wall = [(140.0, -120.0), (260.0, -120.0), (260.0, 120.0), (140.0, 120.0)]
    start = (0.0, 0.0, 0.0)
    goal = (400.0, 0.0, 0.0)
    bounds = (-80.0, 500.0, -200.0, 200.0)
    j = json.dumps({"polygons": [wall]})
    pl = RRTStarPlanner(75.0, seed=11)
    path = pl.plan_if_needed(start, goal, [wall], bounds, [400.0, 0.0, 0.0], j)
    assert len(path) >= 2
    for i in range(len(path) - 1):
        assert not _dubins_collision(path[i], path[i + 1], 75.0, [wall])
    probe_n, probe_e = 200.0, 0.0
    assert point_in_polygon(probe_n, probe_e, wall)
    for i in range(len(path) - 1):
        ln, fn = dubins_interpolate(
            path[i][0], path[i][1], path[i][2], path[i + 1][0], path[i + 1][1], path[i + 1][2], 75.0
        )
        if ln >= 1e8:
            continue
        for k in range(0, 11):
            s = ln * k / 10.0
            n, e, _ = fn(s)
            if point_in_polygon(n, e, wall):
                raise AssertionError("path enters NFZ")


def test_rrt_no_replan_if_goal_unchanged() -> None:
    start = (0.0, 0.0, 0.0)
    goal = (300.0, 50.0, 0.2)
    bounds = (-50.0, 400.0, -100.0, 200.0)
    js = json.dumps({"polygons": []})
    pl = RRTStarPlanner(80.0, seed=3)
    pl.plan_if_needed(start, goal, [], bounds, [300.0, 50.0, 0.2], js)
    assert pl.replan_calls == 1
    pl.plan_if_needed(start, goal, [], bounds, [300.0, 50.0, 0.2], js)
    assert pl.replan_calls == 1
