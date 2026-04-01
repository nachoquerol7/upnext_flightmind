"""GPP ROS 2 node: FL assignment, informed RRT*, takeoff manager."""

from __future__ import annotations

import math
from typing import Any, Optional, Tuple

import rclpy
from geometry_msgs.msg import PoseStamped, Quaternion
from nav_msgs.msg import Path
from rclpy.node import Node
from std_msgs.msg import Float64, Float64MultiArray, String

from gpp.fl_assignment import compute_assigned_fl
from gpp.geometry import parse_geofences_json
from gpp.rrt_star import RRTStarPlanner
from gpp.takeoff_manager import TakeoffConfig, TakeoffManager


def _yaw_to_quat(yaw: float) -> Quaternion:
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class GppNode(Node):
    def __init__(self) -> None:
        super().__init__("gpp_node")
        self.declare_parameter("base_margin_m", 0.0)
        self.declare_parameter("turn_radius_min_m", 600.0)
        self.declare_parameter("vr_mps", 28.0)
        self.declare_parameter("climb_rate_max_mps", 8.0)
        self.declare_parameter("pitch_max_deg", 12.0)

        self._terrain_m: Optional[float] = None
        self._ceiling_m: Optional[float] = None
        self._quality: float = 1.0
        self._goal: Optional[Tuple[float, float, float]] = None
        self._nfz_json: str = ""
        self._nfz_polys: list = []

        self._takeoff_state = [0.0] * 5
        self._own_n_e_h: Tuple[float, float, float] = (0.0, 0.0, 0.0)

        tr = float(self.get_parameter("turn_radius_min_m").get_parameter_value().double_value)
        self._rrt = RRTStarPlanner(tr)
        self._takeoff = TakeoffManager(
            TakeoffConfig(
                vr_mps=float(self.get_parameter("vr_mps").get_parameter_value().double_value),
                climb_rate_max_mps=float(
                    self.get_parameter("climb_rate_max_mps").get_parameter_value().double_value
                ),
                pitch_max_deg=float(self.get_parameter("pitch_max_deg").get_parameter_value().double_value),
            )
        )

        self._pub_fl = self.create_publisher(Float64, "/gpp/assigned_fl", 10)
        self._pub_status = self.create_publisher(String, "/gpp/status", 10)
        self._pub_path = self.create_publisher(Path, "/gpp/global_path", 10)
        self._pub_takeoff = self.create_publisher(String, "/gpp/takeoff_phase", 10)

        self.create_subscription(Float64, "/gpp/terrain_max_m", self._on_terrain, 10)
        self.create_subscription(Float64, "/gpp/ceiling_m", self._on_ceiling, 10)
        self.create_subscription(Float64, "/nav/quality_flag", self._on_quality, 10)
        self.create_subscription(Float64MultiArray, "/gpp/goal", self._on_goal, 10)
        self.create_subscription(String, "/airspace/geofences", self._on_geo, 10)
        self.create_subscription(Float64MultiArray, "/gpp/takeoff_state", self._on_takeoff, 10)
        self.create_subscription(Float64MultiArray, "/ownship/state", self._on_ownship, 10)

        self.create_timer(0.1, self._tick)
        self.get_logger().info("gpp_node started")

    def _on_terrain(self, msg: Float64) -> None:
        self._terrain_m = float(msg.data)

    def _on_ceiling(self, msg: Float64) -> None:
        self._ceiling_m = float(msg.data)

    def _on_quality(self, msg: Float64) -> None:
        self._quality = float(msg.data)

    def _on_goal(self, msg: Float64MultiArray) -> None:
        if len(msg.data) >= 3:
            self._goal = (float(msg.data[0]), float(msg.data[1]), float(msg.data[2]))

    def _on_geo(self, msg: String) -> None:
        self._nfz_json = msg.data
        self._nfz_polys = parse_geofences_json(msg.data)

    def _on_takeoff(self, msg: Float64MultiArray) -> None:
        d = list(msg.data) + [0.0] * 5
        self._takeoff_state = d[:5]

    def _on_ownship(self, msg: Float64MultiArray) -> None:
        if len(msg.data) >= 6:
            vn = float(msg.data[3])
            ve = float(msg.data[4])
            h = math.atan2(ve, vn)
            self._own_n_e_h = (float(msg.data[0]), float(msg.data[1]), h)

    def _tick(self) -> None:
        bm = float(self.get_parameter("base_margin_m").get_parameter_value().double_value)
        if self._terrain_m is None or self._ceiling_m is None:
            self._pub_status.publish(String(data="WAITING"))
            return

        fl, st = compute_assigned_fl(self._terrain_m, self._ceiling_m, self._quality, bm)
        self._pub_status.publish(String(data=st))
        self._pub_fl.publish(Float64(data=fl if st == "OK" else float("nan")))

        if self._goal is not None:
            start = self._own_n_e_h
            g = self._goal
            goal_se2 = (g[0], g[1], g[2])
            gn, ge, _ = goal_se2
            pad = 150.0
            start_n, start_e, _ = self._own_n_e_h
            bounds = (
                min(start_n, gn) - pad,
                max(start_n, gn) + pad,
                min(start_e, ge) - pad,
                max(start_e, ge) + pad,
            )
            gt = [g[0], g[1], g[2]]
            path_states = self._rrt.plan_if_needed(
                start, goal_se2, self._nfz_polys, bounds, gt, self._nfz_json
            )
            path = Path()
            path.header.frame_id = "map"
            path.header.stamp = self.get_clock().now().to_msg()
            for n, e, h in path_states:
                ps = PoseStamped()
                ps.header = path.header
                ps.pose.position.x = n
                ps.pose.position.y = e
                ps.pose.position.z = 0.0
                ps.pose.orientation = _yaw_to_quat(h)
                path.poses.append(ps)
            self._pub_path.publish(path)

        v, rw, agl, vs, dcl = self._takeoff_state
        self._takeoff.update(
            v, rw, agl, vs, desired_climb_mps=max(0.1, dcl if dcl > 0 else 6.0)
        )
        self._pub_takeoff.publish(String(data=self._takeoff.phase))


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = GppNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
