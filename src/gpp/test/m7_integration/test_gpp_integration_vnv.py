from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest
from std_msgs.msg import Float64, Float64MultiArray, String

from gpp.fl_assignment import compute_assigned_fl
from gpp.rrt_star import RRTStarPlanner


def test_tc_int_001_five_waypoints_sequence_replans_and_paths_safe() -> None:
    planner = RRTStarPlanner(75.0, max_iter=700, seed=10)
    start = (0.0, 0.0, 0.0)
    goals = [(300.0, 0.0, 0.0), (350.0, 50.0, 0.2), (400.0, 20.0, 0.1), (450.0, -40.0, -0.1), (500.0, 0.0, 0.0)]
    for g in goals:
        path = planner.plan_if_needed(start, g, [], (-100.0, 600.0, -200.0, 200.0), list(g), json.dumps({"polygons": []}))
        assert len(path) >= 2
        start = path[-1]
    assert planner.replan_calls == 5


def test_tc_int_002_fl_changes_with_quality_to_hold() -> None:
    fl1, st1 = compute_assigned_fl(1000.0, 8000.0, 0.9, 0.0)
    fl2, st2 = compute_assigned_fl(1000.0, 8000.0, 0.6, 0.0)
    fl3, st3 = compute_assigned_fl(1000.0, 8000.0, 0.3, 0.0)
    assert st1 == "OK" and st2 == "OK" and st3 == "HOLD"
    assert fl2 > fl1
    assert math.isnan(fl3)


def test_tc_int_003_dynamic_nfz_change_forces_replan() -> None:
    planner = RRTStarPlanner(75.0, seed=5)
    start, goal = (0.0, 0.0, 0.0), (400.0, 0.0, 0.0)
    bounds = (-100.0, 500.0, -200.0, 200.0)
    planner.plan_if_needed(start, goal, [], bounds, [400.0, 0.0, 0.0], "a")
    wall = [(140.0, -120.0), (260.0, -120.0), (260.0, 120.0), (140.0, 120.0)]
    planner.plan_if_needed(start, goal, [wall], bounds, [400.0, 0.0, 0.0], "b")
    assert planner.replan_calls == 2


@pytest.mark.ros
def test_tc_int_004_global_path_z_is_zero(gpp_runtime: SimpleNamespace) -> None:
    gpp_runtime.pubs.terrain.publish(Float64(data=1000.0))
    gpp_runtime.pubs.ceiling.publish(Float64(data=8000.0))
    gpp_runtime.pubs.quality.publish(Float64(data=0.9))
    gpp_runtime.pubs.goal.publish(Float64MultiArray(data=[300.0, 0.0, 0.0]))
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.path is not None and len(gpp_runtime.cap.path.poses) >= 2, timeout_sec=2.0)
    for ps in gpp_runtime.cap.path.poses:
        assert ps.pose.position.z == 0.0


@pytest.mark.ros
def test_tc_int_005_five_missions_memory_growth_below_5mb(gpp_runtime: SimpleNamespace) -> None:
    psutil = pytest.importorskip("psutil")
    proc = psutil.Process()
    rss0 = proc.memory_info().rss
    gpp_runtime.pubs.terrain.publish(Float64(data=1000.0))
    gpp_runtime.pubs.ceiling.publish(Float64(data=8000.0))
    gpp_runtime.pubs.quality.publish(Float64(data=0.9))
    for i in range(5):
        gpp_runtime.pubs.geo.publish(String(data=json.dumps({"polygons": []})))
        gpp_runtime.pubs.goal.publish(Float64MultiArray(data=[300.0 + i * 20.0, 10.0 * i, 0.0]))
        assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.path is not None and len(gpp_runtime.cap.path.poses) >= 2, timeout_sec=2.0)
    rss1 = proc.memory_info().rss
    assert (rss1 - rss0) < 5 * 1024 * 1024
