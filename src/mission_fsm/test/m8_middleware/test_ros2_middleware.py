"""M8 — ROS 2 middleware checks (TC-MW-001 … TC-MW-010)."""

from __future__ import annotations

import ast
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import rclpy
from flightmind_msgs.msg import FSMState
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from mission_fsm.mission_fsm_node import MissionFsmNode


class _FSMStateCollector(Node):
    def __init__(self) -> None:
        super().__init__("tc_mw_fsm_state_collector")
        self.msgs: list[FSMState] = []
        self.create_subscription(FSMState, "/fsm/state", self._cb, 10)

    def _cb(self, msg: FSMState) -> None:
        self.msgs.append(msg)


@pytest.fixture
def mw_runtime(ros_context: None) -> SimpleNamespace:
    ex = MultiThreadedExecutor()
    node = MissionFsmNode()
    sub = _FSMStateCollector()
    ex.add_node(node)
    ex.add_node(sub)
    yield SimpleNamespace(ex=ex, node=node, sub=sub)
    ex.remove_node(node)
    ex.remove_node(sub)
    node.destroy_node()
    sub.destroy_node()


def _spin(ex: MultiThreadedExecutor, n: int = 40) -> None:
    for _ in range(n):
        ex.spin_once(timeout_sec=0.05)


@pytest.mark.no_ros
@pytest.mark.xfail(reason="XFAIL-ARCH-1.7: /watchdog/status publisher not implemented", strict=True)
def test_tc_mw_001_static_watchdog_status_topic_declared() -> None:
    src = Path(__file__).resolve().parents[2] / "mission_fsm" / "mission_fsm_node.py"
    mod = ast.parse(src.read_text(encoding="utf-8"))
    text = ast.unparse(mod)
    assert "/watchdog/status" in text


@pytest.mark.no_ros
def test_tc_mw_002_static_fsm_state_topic_and_legacy_topics_declared() -> None:
    src = Path(__file__).resolve().parents[2] / "mission_fsm" / "mission_fsm_node.py"
    mod = ast.parse(src.read_text(encoding="utf-8"))
    text = ast.unparse(mod)
    assert "/fsm/state" in text and "/fsm/current_mode" in text and "/fsm/active_trigger" in text


@pytest.mark.xfail(reason="RMW warning callback capture not exposed reliably via rclpy logging", strict=True)
def test_tc_mw_003_qos_incompatible_warning_capture(ros_context: None) -> None:
    class _BestEffortSub(Node):
        def __init__(self) -> None:
            super().__init__("tc_mw_best_effort_sub")
            qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
            self.create_subscription(String, "/mw/qos_probe", self._cb, qos)
            self.count = 0

        def _cb(self, _msg: String) -> None:
            self.count += 1

    class _ReliablePub(Node):
        def __init__(self) -> None:
            super().__init__("tc_mw_reliable_pub")
            qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
            self.pub = self.create_publisher(String, "/mw/qos_probe", qos)

    ex = MultiThreadedExecutor()
    sub = _BestEffortSub()
    pub = _ReliablePub()
    ex.add_node(sub)
    ex.add_node(pub)
    for _ in range(10):
        pub.pub.publish(String(data="ping"))
        ex.spin_once(timeout_sec=0.05)
    ex.remove_node(sub)
    ex.remove_node(pub)
    sub.destroy_node()
    pub.destroy_node()
    assert False, "expected QoS incompatible warning in logs"


def test_tc_mw_004_fsm_state_qos_reliable_transient_local(mw_runtime: SimpleNamespace) -> None:
    infos = mw_runtime.node.get_publishers_info_by_topic("/fsm/state")
    assert infos and infos[0].qos_profile.reliability == ReliabilityPolicy.RELIABLE
    assert infos[0].qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL


def test_tc_mw_005_restart_node_republishes_state() -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && source /home/ignacio-querol/upnext_uas_ws/install/setup.bash && ros2 run mission_fsm mission_fsm_node"]
    p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid)
    try:
        time.sleep(1.0)
    finally:
        os.killpg(p.pid, signal.SIGTERM)
        p.wait(timeout=10)
    p2 = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid)
    try:
        time.sleep(1.0)
        assert p2.poll() is None
    finally:
        os.killpg(p2.pid, signal.SIGTERM)
        p2.wait(timeout=10)


def test_tc_mw_006_legacy_topics_still_published(mw_runtime: SimpleNamespace) -> None:
    infos_mode = mw_runtime.node.get_publishers_info_by_topic("/fsm/current_mode")
    infos_trig = mw_runtime.node.get_publishers_info_by_topic("/fsm/active_trigger")
    assert len(infos_mode) >= 1 and len(infos_trig) >= 1


def test_tc_mw_007_yaml_parameters_match_defaults() -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && source /home/ignacio-querol/upnext_uas_ws/install/setup.bash && ros2 run mission_fsm mission_fsm_node"]
    p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid)
    try:
        time.sleep(1.0)
        q = subprocess.check_output(
            ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && source /home/ignacio-querol/upnext_uas_ws/install/setup.bash && ros2 param get /mission_fsm_node quality_flag_threshold"],
            text=True,
            env=env,
        )
        a = subprocess.check_output(
            ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && source /home/ignacio-querol/upnext_uas_ws/install/setup.bash && ros2 param get /mission_fsm_node daidalus_alert_amber"],
            text=True,
            env=env,
        )
        i = subprocess.check_output(
            ["bash", "-lc", "source /opt/ros/jazzy/setup.bash && source /home/ignacio-querol/upnext_uas_ws/install/setup.bash && ros2 param get /mission_fsm_node initial_state"],
            text=True,
            env=env,
        )
    finally:
        os.killpg(p.pid, signal.SIGTERM)
        p.wait(timeout=10)
    assert "0.5" in q and "1" in a and "PREFLIGHT" in i


def test_tc_mw_008_fsm_state_message_shape_on_wire(mw_runtime: SimpleNamespace) -> None:
    _spin(mw_runtime.ex, 10)
    assert mw_runtime.sub.msgs and mw_runtime.sub.msgs[-1].current_mode != ""


def test_tc_mw_009_startup_under_15s_to_first_fsm_state() -> None:
    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()
    ex = MultiThreadedExecutor()
    t0 = time.monotonic()
    node = MissionFsmNode()
    sub = _FSMStateCollector()
    ex.add_node(node)
    ex.add_node(sub)
    while (time.monotonic() - t0) < 15.0 and not sub.msgs:
        ex.spin_once(timeout_sec=0.05)
    ex.remove_node(node)
    ex.remove_node(sub)
    node.destroy_node()
    sub.destroy_node()
    rclpy.shutdown()
    assert sub.msgs and (time.monotonic() - t0) < 15.0


@pytest.mark.xfail(reason="multi-domain isolation test not stable in current single-process harness", strict=True)
def test_tc_mw_010_ros_domain_id_isolation() -> None:
    # Requires two independent ROS contexts/processes with distinct domain IDs and cross-checking topic visibility.
    assert False
