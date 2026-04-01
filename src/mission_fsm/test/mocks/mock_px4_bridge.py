"""Mock puente PX4: registra setpoints recibidos en topics reales del stack."""

from __future__ import annotations

from typing import Any, Dict, List

import rclpy
from rclpy.node import Node

try:
    from px4_msgs.msg import TrajectorySetpoint

    _HAS_PX4 = True
except ImportError:
    TrajectorySetpoint = None  # type: ignore[misc, assignment]
    _HAS_PX4 = False


class MockPx4Bridge(Node):
    def __init__(self) -> None:
        super().__init__("mock_px4_bridge")
        self._commands: List[Any] = []
        self._sub_traj = None
        if _HAS_PX4 and TrajectorySetpoint is not None:
            self._sub_traj = self.create_subscription(
                TrajectorySetpoint,
                "/fmu/in/trajectory_setpoint",
                self._on_traj,
                10,
            )
        # GAP-ARCH-PX4: añadir suscripción a otros setpoints (offboard, twist) si el FC los usa.

    def _on_traj(self, msg: Any) -> None:
        self._commands.append(msg)

    def inject(self, field: str, value: Any) -> None:
        raise NotImplementedError("mock_px4_bridge is receive-only")

    def get_received(self, topic: str) -> List[Any]:
        if topic == "/fmu/in/trajectory_setpoint":
            return list(self._commands)
        return []

    @property
    def px4_msgs_available(self) -> bool:
        return _HAS_PX4


def create_mock_px4_bridge() -> MockPx4Bridge:
    return MockPx4Bridge()
