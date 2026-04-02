"""M5 — DAIDALUS alerts (TC-DAI-001 … TC-DAI-012)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_daidalus  # noqa: E402


class _AdvisoryCollector(Node):
    def __init__(self) -> None:
        super().__init__("tc_dai_advisory_collector")
        self.msgs: list[TwistStamped] = []
        self.create_subscription(TwistStamped, "/daidalus/advisory", self._cb, 10)

    def _cb(self, msg: TwistStamped) -> None:
        self.msgs.append(msg)


@pytest.fixture
def mission_fsm_sil_with_daidalus(mission_fsm_sil_harness: SimpleNamespace) -> SimpleNamespace:
    dai = mock_daidalus.create_mock_daidalus()
    mission_fsm_sil_harness.ex.add_node(dai)
    h = SimpleNamespace(**vars(mission_fsm_sil_harness))
    h.daidalus = dai
    yield h
    mission_fsm_sil_harness.ex.remove_node(dai)
    dai.destroy_node()


def _reach_cruise(h: SimpleNamespace) -> None:
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    h.inj.inject("takeoff_complete", True)
    assert h.wait_mode("CRUISE")


def test_tc_dai_001_alert_mid_enters_event(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 1)
    assert mission_fsm_sil_with_daidalus.wait_mode("EVENT")


def test_tc_dai_002_alert_below_amber_keeps_cruise(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 0)
    for _ in range(40):
        mission_fsm_sil_with_daidalus.ex.spin_once(timeout_sec=0.05)
    assert mission_fsm_sil_with_daidalus.fsm._fsm.state == "CRUISE"  # noqa: SLF001


def test_tc_dai_003_alert_high_enters_event(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 2)
    assert mission_fsm_sil_with_daidalus.wait_mode("EVENT")


@pytest.mark.demo
def test_tc_dai_004_alert_near_fast_path_without_hysteresis(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 3)
    assert mission_fsm_sil_with_daidalus.spin_until(
        lambda: "to_event_near_fastpath" in mission_fsm_sil_with_daidalus.cap.triggers,
        timeout_sec=3.0,
    )


def test_tc_dai_005_alert_recovery_level_mapping(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 4)
    assert mission_fsm_sil_with_daidalus.spin_until(
        lambda: "to_recovery" in mission_fsm_sil_with_daidalus.cap.triggers,
        timeout_sec=3.0,
    )


def test_tc_dai_006_event_clears_when_alert_returns_nominal(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 2)
    assert mission_fsm_sil_with_daidalus.wait_mode("EVENT")
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 0)
    mission_fsm_sil_with_daidalus.inj.inject("event_cleared", True)
    assert mission_fsm_sil_with_daidalus.wait_mode("CRUISE")


def test_tc_dai_007_advisory_topic_is_published(ros_context: None) -> None:
    import rclpy
    from rclpy.executors import MultiThreadedExecutor

    ex = MultiThreadedExecutor()
    dai = mock_daidalus.create_mock_daidalus()
    sub = _AdvisoryCollector()
    ex.add_node(dai)
    ex.add_node(sub)
    dai.inject("resolution_advisory", [10.0, 5.0, -1.0])
    for _ in range(20):
        ex.spin_once(timeout_sec=0.05)
    ex.remove_node(dai)
    ex.remove_node(sub)
    dai.destroy_node()
    sub.destroy_node()
    assert len(sub.msgs) >= 1


@pytest.mark.slow
def test_tc_dai_008_daidalus_feed_timeout_raises_fault(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("fsm_feed_enabled", False)
    assert mission_fsm_sil_with_daidalus.spin_until(
        lambda: mission_fsm_sil_with_daidalus.cap.mode.split(":", 1)[0] in ("EVENT", "ABORT", "RTB"),
        timeout_sec=8.0,
    )


@pytest.mark.slow
@pytest.mark.xfail(reason="advisory integration to guidance not implemented", strict=True)
def test_tc_dai_009_advisory_vector_applied_to_guidance(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("resolution_advisory", [25.0, 4.0, -0.5])
    assert mission_fsm_sil_with_daidalus.spin_until(
        lambda: "/guidance/advisory_applied" in mission_fsm_sil_with_daidalus.daidalus.get_received("/guidance"),
        timeout_sec=2.0,
    )


@pytest.mark.xfail(reason="no geofence advisory validator", strict=True)
def test_tc_dai_010_advisory_filtered_by_geofence(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("resolution_advisory", [9999.0, 9999.0, 9999.0])
    assert "advisory_rejected_geofence" in mission_fsm_sil_with_daidalus.cap.triggers


def test_tc_dai_011_alert_to_abort_from_event_via_fdir_emergency(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("alert_level", 2)
    assert mission_fsm_sil_with_daidalus.wait_mode("EVENT")
    mission_fsm_sil_with_daidalus.inj.inject("fdir_emergency", True)
    assert mission_fsm_sil_with_daidalus.spin_until(
        lambda: "event_to_abort" in mission_fsm_sil_with_daidalus.cap.triggers, timeout_sec=5.0
    )


@pytest.mark.xfail(reason="advisory consumption path absent in mission_fsm stack", strict=True)
def test_tc_dai_012_advisory_timestamp_freshness_enforced(mission_fsm_sil_with_daidalus: SimpleNamespace) -> None:
    _reach_cruise(mission_fsm_sil_with_daidalus)
    mission_fsm_sil_with_daidalus.daidalus.inject("resolution_advisory", [1.0, 1.0, 1.0])
    assert "advisory_stale_rejected" in mission_fsm_sil_with_daidalus.cap.triggers
