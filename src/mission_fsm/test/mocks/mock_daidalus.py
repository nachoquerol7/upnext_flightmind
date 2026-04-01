"""Mock DAIDALUS: alert_level + resolution_advisory.

Roadmap pedía geometry_msgs/TwistStamped; el stack real (daidalus_node) usa
std_msgs/Float64MultiArray [hdg_deg, gs, vs] — el mock sigue el sistema real.
"""

from __future__ import annotations

from typing import Any, Dict, List

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float64MultiArray, Int32


class MockDaidalus(Node):
    def __init__(self) -> None:
        super().__init__("mock_daidalus")
        self._pub_alert = self.create_publisher(Int32, "/daidalus/alert_level", 10)
        self._pub_adv = self.create_publisher(TwistStamped, "/daidalus/advisory", 10)
        self._pub_ra = self.create_publisher(Float64MultiArray, "/daidalus/resolution_advisory", 10)
        # GAP-ARCH-BRIDGE: adaptador real requerido; SIL duplica hacia entradas del FSM.
        self._pub_fsm_alert = self.create_publisher(Int32, "/fsm/in/daidalus_alert", 10)
        self._alert = 0
        self._ra = [0.0, 0.0, 0.0]
        self._received: Dict[str, List[Any]] = {}
        self._fsm_feed_enabled = True
        self.create_timer(0.1, self._tick)

    def _tick(self) -> None:
        a = Int32(data=int(self._alert))
        self._pub_alert.publish(a)
        if self._fsm_feed_enabled:
            self._pub_fsm_alert.publish(a)
        adv = TwistStamped()
        adv.header.stamp = self.get_clock().now().to_msg()
        adv.twist.linear.x = float(self._ra[0])
        adv.twist.linear.y = float(self._ra[1])
        adv.twist.linear.z = float(self._ra[2])
        self._pub_adv.publish(adv)
        m = Float64MultiArray()
        m.data = [float(self._ra[0]), float(self._ra[1]), float(self._ra[2])]
        self._pub_ra.publish(m)

    def inject(self, field: str, value: Any) -> None:
        if field == "fsm_feed_enabled":
            self._fsm_feed_enabled = bool(value)
            return
        if field == "alert_level":
            self._alert = int(value)
            if self._fsm_feed_enabled:
                self._pub_fsm_alert.publish(Int32(data=int(self._alert)))
            return
        if field == "resolution_advisory":
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                self._ra = [float(value[0]), float(value[1]), float(value[2])]
                return
            raise ValueError("resolution_advisory expects 3 floats [hdg, gs, vs]")
        raise KeyError(f"unknown field: {field}")

    def get_received(self, topic: str) -> List[Any]:
        return list(self._received.get(topic, []))

    @property
    def alert_level(self) -> int:
        return int(self._alert)


def create_mock_daidalus() -> MockDaidalus:
    return MockDaidalus()
