"""Mock sensores / enlace: batería, GCS heartbeat, C2, motor."""

from __future__ import annotations

from typing import Any, Dict, List

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, Float64MultiArray, Header


class MockSensors(Node):
    def __init__(self) -> None:
        super().__init__("mock_sensors")
        self._pub_batt = self.create_publisher(BatteryState, "/battery_state", 10)
        self._pub_gcs = self.create_publisher(Header, "/gcs_heartbeat", 10)
        self._pub_c2 = self.create_publisher(Bool, "/c2_link_status", 10)
        self._pub_motor = self.create_publisher(Float64MultiArray, "/motor_status", 10)
        self._received: Dict[str, List[Any]] = {}
        self._battery_percent = 0.9
        self._c2 = True
        self._motor = [0.0, 0.0, 0.0, 0.0]
        self.create_timer(0.25, self._tick)

    def _tick(self) -> None:
        b = BatteryState()
        b.header.stamp = self.get_clock().now().to_msg()
        b.percentage = float(self._battery_percent)
        b.present = True
        b.power_supply_status = BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
        self._pub_batt.publish(b)
        h = Header()
        h.stamp = self.get_clock().now().to_msg()
        h.frame_id = "gcs"
        self._pub_gcs.publish(h)
        self._pub_c2.publish(Bool(data=bool(self._c2)))
        m = Float64MultiArray()
        m.data = [float(x) for x in self._motor]
        self._pub_motor.publish(m)

    def inject(self, field: str, value: Any) -> None:
        if field == "battery_percent":
            self._battery_percent = float(value)
            return
        if field == "c2_link_status":
            self._c2 = bool(value)
            return
        if field == "motor_status":
            self._motor = [float(x) for x in value]
            return
        raise KeyError(f"unknown field: {field}")

    def get_received(self, topic: str) -> List[Any]:
        return list(self._received.get(topic, []))


def create_mock_sensors() -> MockSensors:
    return MockSensors()
