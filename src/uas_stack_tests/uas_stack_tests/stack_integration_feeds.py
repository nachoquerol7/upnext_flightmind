"""Feeds estáticos para GPP, FSM, FDIR y aire: integración sin PX4 de misión."""

from __future__ import annotations

from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float64, Float64MultiArray, Int32, String


class StackIntegrationFeeds(Node):
    def __init__(self) -> None:
        super().__init__("stack_integration_feeds")
        self._pub_nav_q = self.create_publisher(Float64, "/nav/quality_flag", 10)
        self._pub_fsm_q = self.create_publisher(Float64, "/fsm/in/quality_flag", 10)
        self._pub_fsm_daa = self.create_publisher(Int32, "/fsm/in/daidalus_alert", 10)
        self._pub_preflight = self.create_publisher(Bool, "/fsm/in/preflight_ok", 10)
        self._pub_c2 = self.create_publisher(Bool, "/fdir/in/c2_heartbeat", 10)
        self._pub_terrain = self.create_publisher(Float64, "/gpp/terrain_max_m", 10)
        self._pub_ceiling = self.create_publisher(Float64, "/gpp/ceiling_m", 10)
        self._pub_goal = self.create_publisher(Float64MultiArray, "/gpp/goal", 10)
        self._pub_geo = self.create_publisher(String, "/airspace/geofences", 10)
        self._pub_takeoff = self.create_publisher(Float64MultiArray, "/gpp/takeoff_state", 10)
        self.create_timer(0.5, self._tick)
        self.get_logger().info("stack_integration_feeds: topics de apoyo al stack")

    def _tick(self) -> None:
        self._pub_nav_q.publish(Float64(data=0.92))
        self._pub_fsm_q.publish(Float64(data=0.92))
        self._pub_fsm_daa.publish(Int32(data=0))
        self._pub_preflight.publish(Bool(data=True))
        self._pub_c2.publish(Bool(data=True))
        self._pub_terrain.publish(Float64(data=600.0))
        self._pub_ceiling.publish(Float64(data=6000.0))
        g = Float64MultiArray()
        g.data = [8000.0, 1500.0, 200.0]
        self._pub_goal.publish(g)
        self._pub_geo.publish(String(data='{"polygons": []}'))
        ts = Float64MultiArray()
        ts.data = [1.0, 0.0, 0.0, 0.0, 0.0]
        self._pub_takeoff.publish(ts)


def main(args: Any = None) -> int:
    rclpy.init(args=args)
    node = StackIntegrationFeeds()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0
