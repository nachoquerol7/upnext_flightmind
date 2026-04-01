"""Inyector SIL: publica en /fsm/in/* con los mismos tipos que mission_fsm_node suscribe."""

from __future__ import annotations

from typing import Any, Dict, List

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float64, Int32

from mission_fsm.mission_fsm_node import _BOOL_TOPICS


class FsmInputInjector(Node):
    """`inject(field, value)` publica un mensaje en el topic ROS correspondiente."""

    def __init__(self) -> None:
        super().__init__("fsm_input_injector")
        self._pub_bool: Dict[str, Any] = {}
        for name in _BOOL_TOPICS:
            self._pub_bool[name] = self.create_publisher(Bool, f"/fsm/in/{name}", 10)
        self._pub_quality = self.create_publisher(Float64, "/fsm/in/quality_flag", 10)
        self._pub_daidalus = self.create_publisher(Int32, "/fsm/in/daidalus_alert", 10)
        self._received: Dict[str, List[Any]] = {}

    def inject(self, field: str, value: Any) -> None:
        if field in self._pub_bool:
            self._pub_bool[field].publish(Bool(data=bool(value)))
            return
        if field == "quality_flag":
            self._pub_quality.publish(Float64(data=float(value)))
            return
        if field == "daidalus_alert":
            self._pub_daidalus.publish(Int32(data=int(value)))
            return
        raise KeyError(f"unknown fsm input field: {field!r}")

    def get_received(self, topic: str) -> List[Any]:
        return list(self._received.get(topic, []))


def create_fsm_input_injector() -> FsmInputInjector:
    return FsmInputInjector()
