from __future__ import annotations

import math
import random
import time
from types import SimpleNamespace

import pytest

from gpp.dubins import dubins_length
from gpp.fl_assignment import compute_assigned_fl
from gpp.geometry import point_in_polygon
from gpp.rrt_star import RRTStarPlanner
from gpp.takeoff_manager import TakeoffManager


def test_sr_gpp_001_fl_never_exceeds_ceiling_100_random_cases() -> None:
    random.seed(0)
    for _ in range(100):
        terrain = random.uniform(0.0, 8000.0)
        ceiling = random.uniform(500.0, 10000.0)
        q = random.uniform(0.5, 1.0)
        margin = random.uniform(0.0, 1000.0)
        fl, st = compute_assigned_fl(terrain, ceiling, q, margin)
        if st == "OK":
            assert fl <= (ceiling * 3.280839895013123) / 100.0 + 1e-9


def test_sr_gpp_002_non_ok_status_always_nan_fl() -> None:
    fl1, st1 = compute_assigned_fl(1000.0, 8000.0, 0.3, 0.0)
    fl2, st2 = compute_assigned_fl(1000.0, 8000.0, 0.9, -10.0)
    assert st1 == "HOLD" and math.isnan(fl1)
    assert st2 == "TERRAIN_INVALID" and math.isnan(fl2)


def test_sr_gpp_003_path_segments_within_bounds_10_plans() -> None:
    planner = RRTStarPlanner(75.0, max_iter=500, seed=12)
    bounds = (-100.0, 600.0, -200.0, 200.0)
    for i in range(10):
        goal = (300.0 + i * 20.0, -50.0 + i * 10.0, 0.0)
        path = planner.plan_if_needed((0.0, 0.0, 0.0), goal, [], bounds, list(goal), f"k{i}")
        for n, e, _ in path:
            assert bounds[0] - 1e-6 <= n <= bounds[1] + 1e-6
            assert bounds[2] - 1e-6 <= e <= bounds[3] + 1e-6


@pytest.mark.xfail(
    reason="GPP-G09: implementación Dubins actual puede subestimar distancia euclidiana en algunos casos",
    strict=True,
)
def test_sr_gpp_004_dubins_length_ge_euclidean_50_random() -> None:
    random.seed(1)
    for _ in range(50):
        a = (random.uniform(-500, 500), random.uniform(-500, 500), random.uniform(-math.pi, math.pi))
        b = (random.uniform(-500, 500), random.uniform(-500, 500), random.uniform(-math.pi, math.pi))
        L = dubins_length(*a, *b, 75.0)
        if math.isfinite(L):
            assert L + 1e-6 >= math.hypot(a[0] - b[0], a[1] - b[1])


def test_sr_gpp_005_abort_is_sticky_100_updates() -> None:
    m = TakeoffManager()
    m.update(20.0, 10.0, 0.0, 0.0)
    assert m.phase == "ABORT"
    for _ in range(100):
        assert m.update(50.0, 5000.0, 200.0, 4.0) == "ABORT"


def test_sr_gpp_006_plan_if_needed_deterministic_same_seed() -> None:
    args = ((0.0, 0.0, 0.0), (450.0, 20.0, 0.1), [], (-100.0, 550.0, -200.0, 200.0), [450.0, 20.0, 0.1], "")
    p1 = RRTStarPlanner(75.0, seed=42).plan_if_needed(*args)
    p2 = RRTStarPlanner(75.0, seed=42).plan_if_needed(*args)
    assert p1 == p2


def test_sr_gpp_007_point_in_polygon_no_exceptions_for_small_polys() -> None:
    for poly in ([], [(0.0, 0.0)], [(0.0, 0.0), (1.0, 1.0)], [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]):
        assert isinstance(point_in_polygon(0.1, 0.1, poly), bool)


@pytest.mark.ros
def test_sr_gpp_008_gpp_node_starts_under_5s(ros_context: None) -> None:
    import rclpy

    from gpp.gpp_node import GppNode

    t0 = time.time()
    node = GppNode()
    rclpy.spin_once(node, timeout_sec=0.01)
    dt = time.time() - t0
    node.destroy_node()
    assert dt < 5.0
