"""M7 — Nav2 interface (TC-NAV-001 … TC-NAV-012)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from nav_msgs.msg import Path as NavPath
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_nav2  # noqa: E402


class _PathCollector(Node):
    def __init__(self) -> None:
        super().__init__("tc_nav2_path_collector")
        self.paths: list[NavPath] = []
        self.create_subscription(NavPath, "/plan", self._cb, 10)

    def _cb(self, msg: NavPath) -> None:
        self.paths.append(msg)


def _spin(ex: MultiThreadedExecutor, n: int = 20) -> None:
    for _ in range(n):
        ex.spin_once(timeout_sec=0.05)


@pytest.fixture
def nav2_runtime(ros_context: None) -> SimpleNamespace:
    ex = MultiThreadedExecutor()
    nav = mock_nav2.create_mock_nav2()
    ex.add_node(nav)
    yield SimpleNamespace(ex=ex, nav=nav)
    ex.remove_node(nav)
    nav.destroy_node()


def test_tc_nav_001_plan_topic_publishes_nav_path(nav2_runtime: SimpleNamespace) -> None:
    sub = _PathCollector()
    nav2_runtime.ex.add_node(sub)
    p = NavPath()
    nav2_runtime.nav.inject("plan", p)
    _spin(nav2_runtime.ex, 20)
    nav2_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert len(sub.paths) >= 1


def test_tc_nav_002_inject_outcome_succeeded_sets_state(nav2_runtime: SimpleNamespace) -> None:
    nav2_runtime.nav.inject("nav_outcome", "SUCCEEDED")
    assert nav2_runtime.nav._outcome == "SUCCEEDED"  # noqa: SLF001


def test_tc_nav_003_inject_outcome_aborted_sets_state(nav2_runtime: SimpleNamespace) -> None:
    nav2_runtime.nav.inject("nav_outcome", "ABORTED")
    assert nav2_runtime.nav._outcome == "ABORTED"  # noqa: SLF001


@pytest.mark.xfail(reason="XFAIL-ARCH-NAV: NavigateToPose action server not implemented", strict=True)
def test_tc_nav_004_navigate_to_pose_action_available(nav2_runtime: SimpleNamespace) -> None:
    assert nav2_runtime.nav.action_available is True


@pytest.mark.xfail(reason="no aerial recovery behavior adapter", strict=True)
def test_tc_nav_005_recovery_behavior_spin_blocked_for_aircraft(nav2_runtime: SimpleNamespace) -> None:
    nav2_runtime.nav.inject("nav_outcome", "ABORTED")
    assert "recovery_spin_blocked" in nav2_runtime.nav.get_received("/nav2/recovery")


@pytest.mark.xfail(reason="XFAIL-ARCH-1.6: no pre-Nav2 geofence validator", strict=True)
def test_tc_nav_006_waypoint_outside_geofence_rejected_before_nav2(nav2_runtime: SimpleNamespace) -> None:
    assert "geofence_reject" in nav2_runtime.nav.get_received("/nav2/precheck")


def test_tc_nav_007_plan_type_enforced(nav2_runtime: SimpleNamespace) -> None:
    with pytest.raises(TypeError):
        nav2_runtime.nav.inject("plan", "not-a-path")


def test_tc_nav_008_unknown_inject_key_raises(nav2_runtime: SimpleNamespace) -> None:
    with pytest.raises(KeyError):
        nav2_runtime.nav.inject("invalid_key", True)


@pytest.mark.xfail(reason="XFAIL-ARCH-1.9: interruption waypoint persistence missing", strict=True)
def test_tc_nav_009_interrupt_waypoint_is_saved(nav2_runtime: SimpleNamespace) -> None:
    assert "interrupt_waypoint_saved" in nav2_runtime.nav.get_received("/mission/state")


def test_tc_nav_010_plan_roundtrip_message_identity(nav2_runtime: SimpleNamespace) -> None:
    sub = _PathCollector()
    nav2_runtime.ex.add_node(sub)
    p = NavPath()
    p.header.frame_id = "map"
    nav2_runtime.nav.inject("plan", p)
    _spin(nav2_runtime.ex, 20)
    nav2_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert sub.paths and sub.paths[-1].header.frame_id == "map"


@pytest.mark.xfail(reason="no UTM interface", strict=True)
def test_tc_nav_011_dynamic_utm_restriction_applied(nav2_runtime: SimpleNamespace) -> None:
    assert "utm_constraint_active" in nav2_runtime.nav.get_received("/utm/constraints")


def test_tc_nav_012_action_server_absent_flag_exposed(nav2_runtime: SimpleNamespace) -> None:
    assert nav2_runtime.nav.action_available is False
