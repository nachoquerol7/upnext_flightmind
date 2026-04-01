#!/usr/bin/env python3
"""Republish PX4 VehicleOdometry as FlightMind NavigationState + quality_flag."""

from __future__ import annotations

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from flightmind_msgs.msg import NavigationState
from std_msgs.msg import Float64

try:
    from px4_msgs.msg import VehicleOdometry
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "navigation_bridge requires px4_msgs in the overlay or an underlay "
        "(e.g. clone PX4/px4_msgs and colcon build)."
    ) from exc


def _upper_triangle_21_to_flat36(pc21: list[float]) -> list[float]:
    """Unpack PX4 upper-triangle pose covariance (21) into row-major 6x6 (36)."""
    out = [0.0] * 36
    k = 0
    for i in range(6):
        for j in range(i, 6):
            if k < len(pc21):
                out[i * 6 + j] = float(pc21[k])
                if i != j:
                    out[j * 6 + i] = float(pc21[k])
            k += 1
    return out


class NavigationBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("navigation_bridge")
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self._last_odom_time: float | None = None
        self._last_odom: VehicleOdometry | None = None
        self.create_subscription(VehicleOdometry, "/fmu/out/vehicle_odometry", self._on_odom, qos)
        self._pub_q = self.create_publisher(Float64, "/nav/quality_flag", 10)
        self._pub_nav = self.create_publisher(NavigationState, "/navigation/state", 10)
        self._timer = self.create_timer(1.0 / 50.0, self._tick)

    def _on_odom(self, msg: VehicleOdometry) -> None:
        self._last_odom = msg
        self._last_odom_time = time.monotonic()

    def _quality_from_cov(self, c0: float) -> float:
        if c0 > 5.0:
            return 0.3
        if c0 > 1.0:
            return 0.7
        return 1.0

    def _tick(self) -> None:
        now = time.monotonic()
        if self._last_odom is None or self._last_odom_time is None:
            q = 0.0
            self._pub_q.publish(Float64(data=q))
            return
        if now - self._last_odom_time > 1.0:
            q = 0.0
            self._pub_q.publish(Float64(data=q))
            return

        msg = self._last_odom
        pc = list(getattr(msg, "pose_covariance", []) or [])
        c0 = float(pc[0]) if len(pc) > 0 else 0.0
        q = self._quality_from_cov(c0)
        self._pub_q.publish(Float64(data=q))

        nav = NavigationState()
        nav.header.stamp = self.get_clock().now().to_msg()
        nav.header.frame_id = "ned"
        pos = list(getattr(msg, "position", [0.0, 0.0, 0.0]))
        while len(pos) < 3:
            pos.append(0.0)
        nav.position_ned = [float(pos[0]), float(pos[1]), float(pos[2])]
        vel = list(getattr(msg, "velocity", [0.0, 0.0, 0.0]))
        while len(vel) < 3:
            vel.append(0.0)
        nav.velocity_ned = [float(vel[0]), float(vel[1]), float(vel[2])]
        quat = list(getattr(msg, "q", [1.0, 0.0, 0.0, 0.0]))
        while len(quat) < 4:
            quat.append(0.0)
        nav.orientation_quat = [float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3])]
        nav.covariance_6x6 = _upper_triangle_21_to_flat36(pc) if len(pc) >= 21 else [0.0] * 36
        nav.quality_flag = float(q)
        nav.fuel_consumed_kg = 0.0
        nav.gnss_available = bool(q > 0.5)
        self._pub_nav.publish(nav)


def main() -> None:
    rclpy.init()
    node = NavigationBridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
