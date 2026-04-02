"""Relay: NavigationState.quality_flag -> /fsm/in/quality_flag (Float64).

Separa la traducción sensorial (navigation_bridge) de las entradas del FSM;
el launch orquesta este nodo junto al bridge.
"""

from __future__ import annotations

from typing import Any

import rclpy
from flightmind_msgs.msg import NavigationState
from rclpy.node import Node
from std_msgs.msg import Float64


class NavigationQualityRelayNode(Node):
    def __init__(self) -> None:
        super().__init__("navigation_quality_relay")
        self._pub = self.create_publisher(Float64, "/fsm/in/quality_flag", 10)
        self.create_subscription(NavigationState, "/navigation/state", self._on_nav, 10)
        self.get_logger().info("relay: /navigation/state -> /fsm/in/quality_flag")

    def _on_nav(self, msg: NavigationState) -> None:
        q = float(msg.quality_flag)
        if q != q or q < 0.0:  # NaN or negative
            q = 0.0
        elif q > 1.0:
            q = 1.0
        self._pub.publish(Float64(data=q))


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = NavigationQualityRelayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
