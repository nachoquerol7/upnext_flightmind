"""SIL mínimo para navigation_bridge (sin hardware).

TC-NAV-BRIDGE-001..003 — rclpy + executor; requiere px4_msgs en el underlay (p. ej. ros2_ws/install/px4_msgs).
"""

from __future__ import annotations

import time

import pytest
import rclpy
from px4_msgs.msg import VehicleOdometry
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64

from navigation_bridge.navigation_bridge_node import NavigationBridgeNode


def _spin_until(ex: MultiThreadedExecutor, pred, *, timeout_sec: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        ex.spin_once(timeout_sec=0.05)
        if pred():
            return True
    return False


@pytest.fixture
def ros_context() -> None:
    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()
    yield
    rclpy.shutdown()


@pytest.fixture
def odom_qos() -> QoSProfile:
    return QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)


def test_tc_nav_bridge_001_node_publishes_quality_flag(ros_context, odom_qos) -> None:
    """TC-NAV-BRIDGE-001: nodo arranca y publica en /nav/quality_flag."""
    bridge = NavigationBridgeNode()
    listener = rclpy.create_node("nav_bridge_tc001_listener")
    last: list[float] = []

    def cb(msg: Float64) -> None:
        last.append(float(msg.data))

    listener.create_subscription(Float64, "/nav/quality_flag", cb, 10)
    ex = MultiThreadedExecutor()
    ex.add_node(bridge)
    ex.add_node(listener)
    try:
        assert _spin_until(ex, lambda: len(last) > 0, timeout_sec=2.0)
    finally:
        ex.remove_node(bridge)
        ex.remove_node(listener)
        bridge.destroy_node()
        listener.destroy_node()


def test_tc_nav_bridge_002_quality_full_when_covariance_low(ros_context, odom_qos) -> None:
    """TC-NAV-BRIDGE-002: quality_flag=1.0 cuando pose_covariance[0] < 1.0 (vía lógica del nodo).

    Con px4_msgs estándar no hay `pose_covariance`; el nodo usa lista vacía → c0=0.0 (<1.0) → 1.0.
    """
    bridge = NavigationBridgeNode()
    pub = rclpy.create_node("nav_bridge_tc002_pub")
    publisher = pub.create_publisher(VehicleOdometry, "/fmu/out/vehicle_odometry", odom_qos)
    listener = rclpy.create_node("nav_bridge_tc002_listener")
    last: float | None = None

    def cb(msg: Float64) -> None:
        nonlocal last
        last = float(msg.data)

    listener.create_subscription(Float64, "/nav/quality_flag", cb, 10)
    ex = MultiThreadedExecutor()
    ex.add_node(bridge)
    ex.add_node(pub)
    ex.add_node(listener)

    msg = VehicleOdometry()
    try:
        publisher.publish(msg)
        assert _spin_until(ex, lambda: last is not None and last >= 1.0, timeout_sec=2.0)
        assert last == 1.0
    finally:
        ex.remove_node(bridge)
        ex.remove_node(pub)
        ex.remove_node(listener)
        bridge.destroy_node()
        pub.destroy_node()
        listener.destroy_node()


def test_tc_nav_bridge_003_quality_zero_when_odom_stale(ros_context, odom_qos) -> None:
    """TC-NAV-BRIDGE-003: quality_flag=0.0 cuando no hay mensajes en > 1 s."""
    bridge = NavigationBridgeNode()
    pub = rclpy.create_node("nav_bridge_tc003_pub")
    publisher = pub.create_publisher(VehicleOdometry, "/fmu/out/vehicle_odometry", odom_qos)
    listener = rclpy.create_node("nav_bridge_tc003_listener")
    samples: list[float] = []

    def cb(msg: Float64) -> None:
        samples.append(float(msg.data))

    listener.create_subscription(Float64, "/nav/quality_flag", cb, 10)
    ex = MultiThreadedExecutor()
    ex.add_node(bridge)
    ex.add_node(pub)
    ex.add_node(listener)

    try:
        publisher.publish(VehicleOdometry())
        assert _spin_until(ex, lambda: len(samples) > 0 and samples[-1] >= 1.0, timeout_sec=2.0)

        # Dejar pasar >1 s de reloj real: el bridge usa time.monotonic() en _tick.
        time.sleep(1.15)

        deadline = time.monotonic() + 2.0
        saw_zero = False
        while time.monotonic() < deadline:
            ex.spin_once(timeout_sec=0.02)
            if samples and samples[-1] == 0.0:
                saw_zero = True
                break
        assert saw_zero, "expected quality_flag 0.0 after >1s without odometry"
    finally:
        ex.remove_node(bridge)
        ex.remove_node(pub)
        ex.remove_node(listener)
        bridge.destroy_node()
        pub.destroy_node()
        listener.destroy_node()
