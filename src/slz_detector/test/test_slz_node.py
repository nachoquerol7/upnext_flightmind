"""Tests slz_detector."""

from __future__ import annotations

import json
import time

import pytest
import rclpy
from geometry_msgs.msg import PoseArray
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String

from slz_detector.cloud_io import list_xyz_points
from slz_detector.slz_node import SlzNode
from slz_detector.terrain_classifier import TerrainClassifier


def test_import_slz_detector() -> None:
    import slz_detector  # noqa: F401


def test_terrain_classifier_stub_score() -> None:
    assert TerrainClassifier().classify(None) == 0.8


def test_tc_slz_001_flat_terrain_high_score() -> None:
    """TC-SLZ-001: terreno plano → score > 0.8."""
    tc = TerrainClassifier()
    flat = [(0.08 * i, 0.06 * (i % 9), 0.0) for i in range(280)]
    assert tc.score(flat, 9.0) > 0.8


def test_tc_slz_002_irregular_terrain_low_score() -> None:
    """TC-SLZ-002: terreno irregular (Z dispersa) → score < 0.4."""
    tc = TerrainClassifier()
    irregular = [(float(i), 0.0, float((i % 5) * 2.0)) for i in range(30)]
    assert tc.score(irregular, 9.0) < 0.4


@pytest.fixture
def ros_context() -> None:
    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()
    yield
    rclpy.shutdown()


def _make_cloud_from_points(
    pts: list[tuple[float, float, float]], frame_id: str = "map"
) -> PointCloud2:
    import struct

    from sensor_msgs.msg import PointField

    msg = PointCloud2()
    msg.header.frame_id = frame_id
    msg.height = 1
    msg.width = len(pts)
    msg.fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = msg.point_step * msg.width
    msg.is_dense = True
    buf = bytearray()
    for x, y, z in pts:
        buf.extend(struct.pack("<fff", float(x), float(y), float(z)))
    msg.data = bytes(buf)
    return msg


def test_tc_slz_003_candidates_when_map_received(ros_context: None) -> None:
    """TC-SLZ-003: con mapa hay ≥1 candidato publicado."""
    node = SlzNode()
    pub = rclpy.create_node("tc_slz_003_pub")
    spy = rclpy.create_node("tc_slz_003_spy")
    last_arr: list[PoseArray] = []

    def cb(msg: PoseArray) -> None:
        last_arr.clear()
        last_arr.append(msg)

    spy.create_subscription(PoseArray, "/slz/candidates", cb, 10)
    map_pub = pub.create_publisher(PointCloud2, "/slam/map", 10)
    pts = [(0.5 + 0.05 * i, 0.5 + 0.02 * i, 0.0) for i in range(80)]
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    ex.add_node(pub)
    ex.add_node(spy)
    try:
        map_pub.publish(_make_cloud_from_points(pts))
        for _ in range(60):
            ex.spin_once(timeout_sec=0.05)
        assert len(last_arr) > 0
        assert len(last_arr[-1].poses) >= 1
    finally:
        ex.remove_node(node)
        ex.remove_node(pub)
        ex.remove_node(spy)
        node.destroy_node()
        pub.destroy_node()
        spy.destroy_node()


def test_slz_node_publishes_within_2s(ros_context: None) -> None:
    node = SlzNode()
    spy = rclpy.create_node("slz_test_spy")
    received: list[bool] = [False]

    def cb(_msg: String) -> None:
        received[0] = True

    spy.create_subscription(String, "/slz/status", cb, 10)
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


def test_cloud_io_roundtrip() -> None:
    pts = [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]
    msg = _make_cloud_from_points(pts)
    assert len(list_xyz_points(msg)) == 2
