"""Mock FDIR (interfaz roadmap M6; no coincide 1:1 con fdir_node real)."""

from __future__ import annotations

import json
from typing import Any, Dict, List

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


class MockFdir(Node):
    def __init__(self) -> None:
        super().__init__("mock_fdir")
        self._pub_status = self.create_publisher(String, "/fdir/status", 10)
        self._pub_emergency = self.create_publisher(Bool, "/fdir/emergency", 10)
        self._pub_faults = self.create_publisher(String, "/fdir/active_faults", 10)
        self.create_subscription(Bool, "/fdir/reset_emergency", self._on_reset, 10)
        self._faults: List[str] = []
        self._emergency = False
        self._status = "OK"
        self._received: Dict[str, List[Any]] = {}
        self.create_timer(0.2, self._tick)

    def _on_reset(self, msg: Bool) -> None:
        self._received.setdefault("/fdir/reset_emergency", []).append(msg.data)
        if msg.data:
            self._emergency = False

    def _tick(self) -> None:
        self._pub_status.publish(String(data=self._status))
        self._pub_emergency.publish(Bool(data=self._emergency))
        self._pub_faults.publish(String(data=json.dumps(self._faults)))

    def inject(self, field: str, value: Any) -> None:
        if field == "status":
            self._status = str(value)
            return
        if field == "emergency":
            self._emergency = bool(value)
            return
        if field == "active_faults":
            self._faults = list(value) if isinstance(value, list) else [str(value)]
            return
        raise KeyError(f"unknown field: {field}")

    def get_received(self, topic: str) -> List[Any]:
        return list(self._received.get(topic, []))


def create_mock_fdir() -> MockFdir:
    return MockFdir()
