"""Mock FastLIO2: Odometry + quality_flag (roadmap)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import rclpy
from geometry_msgs.msg import PoseWithCovariance, TwistWithCovariance
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import Float64, Header


class MockFastlio2(Node):
    """Publica /Odometry y /quality_flag.

    SIL: replica también en /fsm/in/quality_flag lo que consumiría un nodo puente
    hasta el FSM (el nodo de misión no se suscribe a /quality_flag).
    """

    def __init__(self) -> None:
        super().__init__("mock_fastlio2")
        self._pub_odom = self.create_publisher(Odometry, "/Odometry", 10)
        self._pub_q = self.create_publisher(Float64, "/quality_flag", 10)
        # GAP-ARCH-BRIDGE: en vuelo real, un adaptador debería mapear /quality_flag → FSM.
        self._pub_fsm_quality = self.create_publisher(Float64, "/fsm/in/quality_flag", 10)
        self._quality = 1.0
        self._received: Dict[str, List[Any]] = {}
        self._odom = Odometry()
        self._odom.header = Header()
        self._odom.header.frame_id = "map"
        self._odom.child_frame_id = "base_link"
        self._odom.pose = PoseWithCovariance()
        self._odom.twist = TwistWithCovariance()
        self.create_timer(0.1, self._tick)

    def _tick(self) -> None:
        self._odom.header.stamp = self.get_clock().now().to_msg()
        self._pub_odom.publish(self._odom)
        q = Float64(data=float(self._quality))
        self._pub_q.publish(q)
        self._pub_fsm_quality.publish(q)

    def inject(self, field: str, value: Any) -> None:
        if field == "quality_flag":
            self._quality = float(value)
            q = Float64(data=float(self._quality))
            self._pub_fsm_quality.publish(q)
            return
        if field == "odometry":
            self._odom = value
            return
        raise KeyError(f"unknown field: {field}")

    def get_received(self, topic: str) -> List[Any]:
        return list(self._received.get(topic, []))


def create_mock_fastlio2() -> MockFastlio2:
    return MockFastlio2()
