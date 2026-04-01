"""FDIR-019: watchdog de heartbeats de nodos críticos; FDIR-020 complementa heartbeats en productores."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

# (topic, logical_name, emergency_if_dead)
_HEARTBEATS: List[Tuple[str, str, bool]] = [
    ("/fsm/heartbeat", "mission_fsm", True),
    ("/daidalus/heartbeat", "daidalus", True),
    ("/navigation/heartbeat", "navigation_bridge", False),
    ("/acas/heartbeat", "acas", True),
]


class FdirWatchdogNode(Node):
    def __init__(self) -> None:
        super().__init__("fdir_watchdog_node")
        self.declare_parameter("heartbeat_timeout_sec", 3.0)
        self._timeout = float(self.get_parameter("heartbeat_timeout_sec").value)
        now = time.monotonic()
        self._last_rx: Dict[str, float] = {name: now for _, name, _ in _HEARTBEATS}
        self._dead: Dict[str, bool] = {name: False for _, name, _ in _HEARTBEATS}
        self._pub_dead = self.create_publisher(String, "/fdir/node_dead", 10)
        self._pub_emergency = self.create_publisher(Bool, "/fsm/in/fdir_emergency", 10)
        for topic, name, _ in _HEARTBEATS:
            self.create_subscription(Bool, topic, self._mk_cb(name), 10)
        self.create_timer(0.5, self._tick)
        self.get_logger().info("fdir_watchdog_node: timeout=%.1fs", self._timeout)

    def _mk_cb(self, name: str):
        def _cb(_msg: Bool) -> None:
            self._last_rx[name] = time.monotonic()

        return _cb

    def _tick(self) -> None:
        now = time.monotonic()
        any_emergency = False
        for _topic, name, emer in _HEARTBEATS:
            stale = (now - self._last_rx[name]) > self._timeout
            was_dead = self._dead[name]
            if stale and not was_dead:
                self._dead[name] = True
                self._pub_dead.publish(String(data=name))
                self.get_logger().error("node heartbeat lost: %s", name)
            elif not stale and was_dead:
                self._dead[name] = False
                self.get_logger().warn("node heartbeat restored: %s", name)
            if self._dead[name] and emer:
                any_emergency = True
        self._pub_emergency.publish(Bool(data=any_emergency))


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = FdirWatchdogNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
