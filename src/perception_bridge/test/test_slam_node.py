"""Tests perception_bridge / SLAM."""

from __future__ import annotations

import time

import pytest
import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import Imu, PointCloud2
from std_msgs.msg import Float64

from perception_bridge.point_cloud_utils import pointcloud2_from_xyz
from perception_bridge.slam_node import SlamNode


def test_import_perception_bridge() -> None:
    import perception_bridge  # noqa: F401
    import perception_bridge.point_cloud_utils as pcu  # noqa: F401


@pytest.fixture
def ros_context() -> None:
    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()
    yield
    rclpy.shutdown()


def test_slam_node_publishes_within_2s(ros_context: None) -> None:
    node = SlamNode()
    spy = rclpy.create_node("slam_test_spy")
    received: list[bool] = [False]

    def cb(_msg: PoseWithCovarianceStamped) -> None:
        received[0] = True

    spy.create_subscription(PoseWithCovarianceStamped, "/slam/pose", cb, 10)
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    ex.add_node(spy)
    deadline = time.monotonic() + 2.0
    try:
        while time.monotonic() < deadline and not received[0]:
            ex.spin_once(timeout_sec=0.05)
        assert received[0]
    finally:
        ex.remove_node(node)
        ex.remove_node(spy)
        node.destroy_node()
        spy.destroy_node()


def test_tc_slam_001_quality_rises_with_dense_cloud(ros_context: None) -> None:
    """TC-SLAM-001: calidad (/slam/quality y override) sube con nube densa frente a dispersa."""
    node = SlamNode()
    pub = rclpy.create_node("tc_slam_001_pub")
    spy = rclpy.create_node("tc_slam_001_spy")
    last_q: list[float] = []
    last_nav: list[float] = []

    def q_cb(msg: Float64) -> None:
        last_q.clear()
        last_q.append(float(msg.data))

    def nav_cb(msg: Float64) -> None:
        last_nav.clear()
        last_nav.append(float(msg.data))

    spy.create_subscription(Float64, "/slam/quality", q_cb, 10)
    spy.create_subscription(Float64, "/nav/quality_override", nav_cb, 10)
    pub_scan = pub.create_publisher(PointCloud2, "/scan", 10)

    sparse = [(i * 5.0, 0.0, 0.0) for i in range(4)]
    dense = [(0.01 * (i % 20), 0.01 * (i // 20), 0.0) for i in range(400)]

    ex = SingleThreadedExecutor()
    ex.add_node(node)
    ex.add_node(pub)
    ex.add_node(spy)
    try:
        for _ in range(30):
            ex.spin_once(timeout_sec=0.02)
        pub_scan.publish(pointcloud2_from_xyz(sparse, frame_id="map"))
        for _ in range(40):
            ex.spin_once(timeout_sec=0.02)
        q_sparse = last_q[0] if last_q else 0.0
        nav_sparse = last_nav[0] if last_nav else 0.0

        pub_scan.publish(pointcloud2_from_xyz(dense, frame_id="map"))
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            ex.spin_once(timeout_sec=0.02)
        q_dense = last_q[0] if last_q else 0.0
        nav_dense = last_nav[0] if last_nav else 0.0

        assert q_dense > q_sparse + 0.1
        assert nav_dense >= nav_sparse
        assert nav_dense >= 0.7
    finally:
        ex.remove_node(node)
        ex.remove_node(pub)
        ex.remove_node(spy)
        node.destroy_node()
        pub.destroy_node()
        spy.destroy_node()


def test_tc_slam_002_pose_updates_with_imu(ros_context: None) -> None:
    """TC-SLAM-002: la orientación (pose) cambia al publicar gyro en /imu/data."""
    node = SlamNode()
    pub = rclpy.create_node("tc_slam_002_pub")
    imu_pub = pub.create_publisher(Imu, "/imu/data", 10)
    orientations: list[tuple[float, float, float, float]] = []

    def pose_cb(msg: PoseWithCovarianceStamped) -> None:
        o = msg.pose.pose.orientation
        orientations.append((float(o.w), float(o.x), float(o.y), float(o.z)))

    spy = rclpy.create_node("tc_slam_002_spy")
    spy.create_subscription(PoseWithCovarianceStamped, "/slam/pose", pose_cb, 10)

    ex = SingleThreadedExecutor()
    ex.add_node(node)
    ex.add_node(pub)
    ex.add_node(spy)
    try:
        for _ in range(10):
            ex.spin_once(timeout_sec=0.02)
        w0 = orientations[-1][0] if orientations else 1.0

        imu = Imu()
        imu.header.frame_id = "base_link"
        imu.linear_acceleration.z = 9.81
        imu.angular_velocity.z = 0.85
        for _ in range(80):
            imu_pub.publish(imu)
            ex.spin_once(timeout_sec=0.02)

        assert len(orientations) >= 2
        w1 = orientations[-1][0]
        x1 = orientations[-1][1]
        y1 = orientations[-1][2]
        z1 = orientations[-1][3]
        assert abs(w1 - w0) > 1e-4 or abs(x1) + abs(y1) + abs(z1) > 1e-4
    finally:
        ex.remove_node(node)
        ex.remove_node(pub)
        ex.remove_node(spy)
        node.destroy_node()
        pub.destroy_node()
        spy.destroy_node()
