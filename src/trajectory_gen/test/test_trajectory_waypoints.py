"""TC-TRAJ-001..004 — waypoint follower core."""

from __future__ import annotations

import pytest

from trajectory_gen.waypoint_follower import WaypointFollower, ned_distance


@pytest.mark.no_ros
def test_tc_traj_001_waypoints_followed_in_order() -> None:
    f = WaypointFollower(waypoint_radius_m=1.0)
    f.set_path([(0.0, 0.0, 0.0), (100.0, 0.0, 0.0), (100.0, 100.0, 0.0)])
    assert f.wp_idx == 0
    f.step((0.0, 0.0, 0.0), 20.0)
    assert f.wp_idx == 1
    f.step((100.0, 0.0, 0.0), 20.0)
    assert f.wp_idx == 2


@pytest.mark.no_ros
def test_tc_traj_002_mission_complete_last_wp() -> None:
    f = WaypointFollower(1.0)
    f.set_path([(0.0, 0.0, 0.0), (5.0, 0.0, 0.0)])
    f.step((0.0, 0.0, 0.0), 10.0)
    _, _, done = f.step((5.0, 0.0, 0.0), 10.0)
    assert done


@pytest.mark.no_ros
def test_tc_traj_003_replanner_flag_resets_path() -> None:
    f = WaypointFollower(1.0)
    f.set_path([(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)])
    f.wp_idx = 1
    f.set_path([(0.0, 0.0, 0.0)])
    assert f.wp_idx == 0


@pytest.mark.no_ros
def test_tc_traj_004_distance_metric() -> None:
    assert ned_distance([0, 0, 0], [3, 4, 0]) == pytest.approx(5.0)
