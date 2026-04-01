"""ROS 2 node: BatteryState -> /fsm/in/battery_low, /fsm/in/battery_critical (FDIR-004)."""

from __future__ import annotations

from typing import Any

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool

from fdir.battery_monitor import BatteryMonitor


class BatteryMonitorNode(Node):
    def __init__(self) -> None:
        super().__init__("battery_monitor_node")
        self.declare_parameter("low_threshold", 0.30)
        self.declare_parameter("critical_threshold", 0.10)
        low = float(self.get_parameter("low_threshold").value)
        crit = float(self.get_parameter("critical_threshold").value)
        self._mon = BatteryMonitor(low_threshold=low, critical_threshold=crit)
        self._pub_low = self.create_publisher(Bool, "/fsm/in/battery_low", 10)
        self._pub_crit = self.create_publisher(Bool, "/fsm/in/battery_critical", 10)
        self.create_subscription(BatteryState, "/battery_state", self._on_battery, 10)
        self._last_low = False
        self._last_crit = False
        self.get_logger().info("battery_monitor_node: FDIR-004 thresholds low=%.2f crit=%.2f", low, crit)

    def _on_battery(self, msg: BatteryState) -> None:
        pct = float(msg.percentage) if msg.percentage >= 0.0 else 1.0
        level_fault = self._mon.update(pct)
        low = level_fault == "BATTERY_LOW"
        crit = level_fault == "BATTERY_CRITICAL"
        if low != self._last_low:
            self._pub_low.publish(Bool(data=low))
            self._last_low = low
        if crit != self._last_crit:
            self._pub_crit.publish(Bool(data=crit))
            self._last_crit = crit


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = BatteryMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
