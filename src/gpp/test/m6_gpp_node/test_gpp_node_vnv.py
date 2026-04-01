from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest
import rclpy
from rclpy.qos import QoSReliabilityPolicy
from std_msgs.msg import Float64, Float64MultiArray, String


def _publish_nominal_inputs(rt: SimpleNamespace) -> None:
    rt.pubs.terrain.publish(Float64(data=1000.0))
    rt.pubs.ceiling.publish(Float64(data=8000.0))
    rt.pubs.quality.publish(Float64(data=0.9))
    rt.pubs.ownship.publish(Float64MultiArray(data=[0.0, 0.0, 0.0, 20.0, 0.0, 0.0]))
    rt.spin_for(0.3)


@pytest.mark.ros
def test_tc_node_001_node_starts_and_topics_exist(gpp_runtime: SimpleNamespace) -> None:
    gpp_runtime.spin_for(0.2)
    topics = dict(gpp_runtime.node.get_topic_names_and_types())
    for t in ("/gpp/assigned_fl", "/gpp/status", "/gpp/global_path", "/gpp/takeoff_phase"):
        assert t in topics


@pytest.mark.ros
def test_tc_node_002_missing_terrain_or_ceiling_publishes_waiting(gpp_runtime: SimpleNamespace) -> None:
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.status == "WAITING", timeout_sec=1.5)


@pytest.mark.ros
def test_tc_node_003_nominal_inputs_publish_ok_and_finite_fl(gpp_runtime: SimpleNamespace) -> None:
    _publish_nominal_inputs(gpp_runtime)
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.status == "OK", timeout_sec=1.5)
    assert gpp_runtime.cap.fl is not None and math.isfinite(gpp_runtime.cap.fl)


@pytest.mark.ros
def test_tc_node_004_low_quality_publishes_hold(gpp_runtime: SimpleNamespace) -> None:
    gpp_runtime.pubs.terrain.publish(Float64(data=1000.0))
    gpp_runtime.pubs.ceiling.publish(Float64(data=8000.0))
    gpp_runtime.pubs.quality.publish(Float64(data=0.3))
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.status == "HOLD", timeout_sec=1.5)


@pytest.mark.ros
def test_tc_node_005_goal_published_emits_path(gpp_runtime: SimpleNamespace) -> None:
    _publish_nominal_inputs(gpp_runtime)
    gpp_runtime.pubs.goal.publish(Float64MultiArray(data=[300.0, 0.0, 0.0]))
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.path is not None and len(gpp_runtime.cap.path.poses) >= 2, timeout_sec=2.0)


@pytest.mark.ros
def test_tc_node_006_same_goal_twice_identical_path(gpp_runtime: SimpleNamespace) -> None:
    _publish_nominal_inputs(gpp_runtime)
    gpp_runtime.pubs.goal.publish(Float64MultiArray(data=[300.0, 40.0, 0.1]))
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.path is not None and len(gpp_runtime.cap.path.poses) >= 2, timeout_sec=2.0)
    p1 = [(p.pose.position.x, p.pose.position.y) for p in gpp_runtime.cap.path.poses]
    gpp_runtime.pubs.goal.publish(Float64MultiArray(data=[300.0, 40.0, 0.1]))
    gpp_runtime.spin_for(0.4)
    p2 = [(p.pose.position.x, p.pose.position.y) for p in gpp_runtime.cap.path.poses]
    assert p1 == p2


@pytest.mark.ros
def test_tc_node_007_nfz_path_avoids_forbidden_zone(gpp_runtime: SimpleNamespace) -> None:
    _publish_nominal_inputs(gpp_runtime)
    wall = [(140.0, -30.0), (260.0, -30.0), (260.0, 30.0), (140.0, 30.0)]
    gpp_runtime.pubs.geo.publish(String(data=json.dumps({"polygons": [wall]})))
    gpp_runtime.pubs.goal.publish(Float64MultiArray(data=[400.0, 80.0, 0.0]))
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.path is not None and len(gpp_runtime.cap.path.poses) >= 2, timeout_sec=2.5)
    for ps in gpp_runtime.cap.path.poses:
        x = ps.pose.position.x
        y = ps.pose.position.y
        assert not (140.0 < x < 260.0 and -30.0 < y < 30.0)


@pytest.mark.ros
def test_tc_node_008_bounds_include_start_far_from_origin(gpp_runtime: SimpleNamespace) -> None:
    _publish_nominal_inputs(gpp_runtime)
    gpp_runtime.pubs.ownship.publish(Float64MultiArray(data=[10000.0, 10000.0, 0.0, 10.0, 0.0, 0.0]))
    gpp_runtime.pubs.goal.publish(Float64MultiArray(data=[10200.0, 10050.0, 0.0]))
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.path is not None and len(gpp_runtime.cap.path.poses) >= 2, timeout_sec=2.5)
    p0 = gpp_runtime.cap.path.poses[0].pose.position
    assert abs(p0.x - 10000.0) < 1e-6 and abs(p0.y - 10000.0) < 1e-6


@pytest.mark.ros
def test_tc_node_009_base_margin_parameter_affects_fl(gpp_runtime: SimpleNamespace) -> None:
    gpp_runtime.node.set_parameters([rclpy.parameter.Parameter("base_margin_m", value=100.0)])
    _publish_nominal_inputs(gpp_runtime)
    assert gpp_runtime.wait_until(lambda: gpp_runtime.cap.status == "OK", timeout_sec=1.5)
    assert gpp_runtime.cap.fl is not None
    assert gpp_runtime.cap.fl > (1000.0 * 3.280839895013123 + 300.0) / 100.0


@pytest.mark.ros
def test_tc_node_010_qos_reliability_document_current(gpp_runtime: SimpleNamespace) -> None:
    infos_fl = gpp_runtime.node.get_publishers_info_by_topic("/gpp/assigned_fl")
    infos_st = gpp_runtime.node.get_publishers_info_by_topic("/gpp/status")
    assert infos_fl and infos_st
    assert infos_fl[0].qos_profile.reliability == QoSReliabilityPolicy.RELIABLE
    assert infos_st[0].qos_profile.reliability == QoSReliabilityPolicy.RELIABLE
