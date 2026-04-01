"""ROS 2 node: C2 heartbeat -> /fsm/in/c2_lost (FDIR-003)."""

from __future__ import annotations

from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

from fdir.c2_monitor import C2Monitor


class C2MonitorNode(Node):
    def __init__(self) -> None:
        super().__init__("fdir_c2_monitor_node")
        self.declare_parameter("timeout_sec", 5.0)
        self.declare_parameter("check_hz", 20.0)
        to = float(self.get_parameter("timeout_sec").value)
        self._mon = C2Monitor(timeout_sec=to)
        self._pub = self.create_publisher(Bool, "/fsm/in/c2_lost", 10)
        self.create_subscription(Bool, "/c2_link_status", self._on_c2, 10)
        hz = max(1.0, float(self.get_parameter("check_hz").value))
        self.create_timer(1.0 / hz, self._tick)
        self._last_lost = False
        self.get_logger().info("fdir_c2_monitor_node: FDIR-003 timeout=%.1fs", to)

    def _on_c2(self, msg: Bool) -> None:
        if bool(msg.data):
            self._mon.heartbeat()

    def _tick(self) -> None:
        lost = self._mon.check()
        if lost != self._last_lost:
            self._pub.publish(Bool(data=lost))
            self._last_lost = lost


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = C2MonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
