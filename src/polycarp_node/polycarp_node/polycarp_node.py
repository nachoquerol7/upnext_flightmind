"""PolyCARP geofence node."""

from __future__ import annotations

import math
import os
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float64, Float64MultiArray, String

from polycarp_node.polycarp_core import evaluate_geofence_threat, parse_geofences_json


class PolycarpNode(Node):
    def __init__(self) -> None:
        super().__init__("polycarp_node")
        self.declare_parameter("imminent_horizon_s", 60.0)
        self.declare_parameter("geofence_config_file", "")

        self._n = self._e = self._z = 0.0
        self._vn = self._ve = self._vd = 0.0
        self._have_own = False
        self._polys: list = []
        self._geo_json = ""

        cfg = self.get_parameter("geofence_config_file").get_parameter_value().string_value.strip()
        if cfg and os.path.isfile(cfg):
            with open(cfg, encoding="utf-8") as f:
                self._geo_json = f.read()
            self._polys = parse_geofences_json(self._geo_json)

        self._pub_imm = self.create_publisher(Bool, "/polycarp/violation_imminent", 10)
        self._pub_ttv = self.create_publisher(Float64, "/polycarp/time_to_violation", 10)

        self.create_subscription(Float64MultiArray, "/ownship/state", self._on_own, 10)
        self.create_subscription(String, "/airspace/geofences", self._on_geo, 10)
        self.create_timer(0.1, self._tick)

        self.get_logger().info("polycarp_node ready")

    def _on_own(self, msg: Float64MultiArray) -> None:
        if len(msg.data) < 6:
            return
        self._n = float(msg.data[0])
        self._e = float(msg.data[1])
        self._z = float(msg.data[2])
        self._vn = float(msg.data[3])
        self._ve = float(msg.data[4])
        self._vd = float(msg.data[5])
        self._have_own = True

    def _on_geo(self, msg: String) -> None:
        self._geo_json = msg.data
        self._polys = parse_geofences_json(msg.data)

    def _tick(self) -> None:
        if not self._have_own:
            return
        hz = float(self.get_parameter("imminent_horizon_s").get_parameter_value().double_value)
        imm, ttv = evaluate_geofence_threat(
            self._n, self._e, self._vn, self._ve, self._polys, imminent_horizon_s=hz
        )
        self._pub_imm.publish(Bool(data=imm))
        t_out = float(ttv) if math.isfinite(ttv) else -1.0
        self._pub_ttv.publish(Float64(data=t_out))


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = PolycarpNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
