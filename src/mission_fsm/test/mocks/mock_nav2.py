"""Mock Nav2: publica /plan. Servidor /navigate_to_pose requiere nav2_msgs (GAP-ARCH-NAV2)."""

from __future__ import annotations

from typing import Any, Dict, List

import rclpy
from nav_msgs.msg import Path
from rclpy.node import Node

# GAP-ARCH-NAV2: instalar ros-jazzy-nav2-msgs y generar ActionServer NavigateToPose aquí.


class MockNav2(Node):
    def __init__(self) -> None:
        super().__init__("mock_nav2")
        self._pub_plan = self.create_publisher(Path, "/plan", 10)
        self._received: Dict[str, List[Any]] = {}
        self._outcome = "SUCCEEDED"

    def inject(self, field: str, value: Any) -> None:
        if field == "nav_outcome":
            self._outcome = str(value)
            return
        if field == "plan":
            if not isinstance(value, Path):
                raise TypeError("plan must be nav_msgs/Path")
            self._pub_plan.publish(value)
            return
        raise KeyError(f"unknown field: {field}")

    def get_received(self, topic: str) -> List[Any]:
        return list(self._received.get(topic, []))

    @property
    def action_available(self) -> bool:
        return False


def create_mock_nav2() -> MockNav2:
    return MockNav2()
