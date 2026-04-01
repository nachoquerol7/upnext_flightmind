"""Subscribe paths + vehicle state; publish discretised Dubins 3D setpoints."""

from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple

import rclpy
from flightmind_msgs.msg import NavigationState, TrajectorySetpoint
from geometry_msgs.msg import Quaternion
from nav_msgs.msg import Path
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile
from std_msgs.msg import Bool, Float64MultiArray, Int32, String

from trajectory_gen.dubins3d import (
    build_full_path_setpoints,
    vehicle_model_from_state_vector,
)
from trajectory_gen.waypoint_follower import WaypointFollower, path_to_ned_waypoints


def quat_to_heading(q: Quaternion) -> float:
    """Yaw from North (rad), CCW — works for level attitudes."""
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


def path_has_leg(p: Optional[Path]) -> bool:
    return p is not None and len(p.poses) >= 2


def select_input_path(adjusted: Optional[Path], global_path: Optional[Path]) -> Optional[Path]:
    if path_has_leg(adjusted):
        return adjusted
    if path_has_leg(global_path):
        return global_path
    return None


def path_to_waypoints_nezh(path: Path) -> List[Tuple[float, float, float, float]]:
    out: List[Tuple[float, float, float, float]] = []
    for ps in path.poses:
        pos = ps.pose.position
        h = quat_to_heading(ps.pose.orientation)
        out.append((float(pos.x), float(pos.y), float(pos.z), h))
    return out


class TrajectoryGenNode(Node):
    def __init__(self) -> None:
        super().__init__("trajectory_gen_node")
        self.declare_parameter("cruise_speed_ms", -1.0)
        self.declare_parameter("use_waypoint_follower", False)
        self.declare_parameter("waypoint_radius_m", 5.0)
        self.declare_parameter("follower_cruise_ms", 25.0)

        latched = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
        )
        self._adjusted_path: Optional[Path] = None
        self._global_path: Optional[Path] = None
        self._vm_data: List[float] = []
        self._daa_alert = 0
        self._last_pub_ns = 0
        self._nav_pos: Optional[List[float]] = None
        self._repl_active = False
        self._path_gpp_alias: Optional[Path] = None
        self._path_repl: Optional[Path] = None
        self._follower = WaypointFollower(float(self.get_parameter("waypoint_radius_m").value))
        self._mission_complete_sent = False

        self._pub_sp = self.create_publisher(Float64MultiArray, "/trajectory/setpoints", 10)
        self._pub_st = self.create_publisher(String, "/trajectory_gen/status", 10)
        self._pub_inf = self.create_publisher(String, "/trajectory_gen/infeasible_reason", 10)
        self._pub_esc = self.create_publisher(String, "/local_replanner/trajectory_infeasible", 10)

        self.create_subscription(Path, "/local_replanner/adjusted_path", self._on_adj, 10)
        self.create_subscription(Path, "/gpp/global_path", self._on_glob, 10)
        self.create_subscription(Path, "/gpp/path", self._on_gpp_path, 10)
        self.create_subscription(Path, "/local_replanner/path", self._on_repl_path_msg, 10)
        self.create_subscription(NavigationState, "/navigation/state", self._on_nav_state, 10)
        self.create_subscription(Bool, "/local_replanner/status", self._on_repl_status, 10)
        self.create_subscription(Float64MultiArray, "/vehicle_model/state", self._on_vm, latched)
        self.create_subscription(Int32, "/daidalus/alert_level", self._on_daa, 10)

        self._pub_traj_setpoint = self.create_publisher(TrajectorySetpoint, "/trajectory/setpoint", 10)
        self._pub_progress = self.create_publisher(String, "/trajectory/progress", 10)
        self._pub_mission_complete = self.create_publisher(Bool, "/fsm/in/mission_complete", 10)

        self.create_timer(0.05, self._tick)
        self.create_timer(1.0 / 50.0, self._tick_follower)
        self.get_logger().info("trajectory_gen_node started (base tick 20 Hz; output throttled)")

    def _on_adj(self, msg: Path) -> None:
        self._adjusted_path = msg

    def _on_glob(self, msg: Path) -> None:
        self._global_path = msg

    def _on_vm(self, msg: Float64MultiArray) -> None:
        self._vm_data = [float(x) for x in msg.data]

    def _on_daa(self, msg: Int32) -> None:
        self._daa_alert = int(msg.data)

    def _on_gpp_path(self, msg: Path) -> None:
        self._path_gpp_alias = msg
        if not self._repl_active:
            self._reset_follower_from_path(msg)

    def _on_repl_path_msg(self, msg: Path) -> None:
        self._path_repl = msg
        if self._repl_active:
            self._reset_follower_from_path(msg)

    def _on_repl_status(self, msg: Bool) -> None:
        self._repl_active = bool(msg.data)
        if self._repl_active and self._path_repl is not None:
            self._reset_follower_from_path(self._path_repl)
        elif not self._repl_active and self._path_gpp_alias is not None:
            self._reset_follower_from_path(self._path_gpp_alias)

    def _on_nav_state(self, msg: NavigationState) -> None:
        self._nav_pos = [float(msg.position_ned[0]), float(msg.position_ned[1]), float(msg.position_ned[2])]

    def _reset_follower_from_path(self, path: Path) -> None:
        if len(path.poses) < 1:
            return
        r = float(self.get_parameter("waypoint_radius_m").value)
        self._follower = WaypointFollower(r)
        self._follower.set_path(path_to_ned_waypoints(path.poses))
        self._mission_complete_sent = False

    def _tick_follower(self) -> None:
        if not bool(self.get_parameter("use_waypoint_follower").value):
            return
        if self._nav_pos is None:
            return
        cruise = float(self.get_parameter("follower_cruise_ms").value)
        if not self._follower.waypoints:
            src = self._path_repl if self._repl_active and self._path_repl else self._path_gpp_alias
            if src is None or len(src.poses) < 1:
                return
            self._reset_follower_from_path(src)

        tgt, dist, complete = self._follower.step(self._nav_pos, cruise)
        if complete and not self._mission_complete_sent:
            self._pub_mission_complete.publish(Bool(data=True))
            self._mission_complete_sent = True
            self._pub_progress.publish(String(data="complete"))
            return
        if tgt is None:
            return
        vn, ve, vd = self._follower.velocity_toward(self._nav_pos, cruise)
        sp = TrajectorySetpoint()
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.header.frame_id = "ned"
        sp.position_ned = [float(tgt[0]), float(tgt[1]), float(tgt[2])]
        sp.velocity_ned = [float(vn), float(ve), float(vd)]
        self._pub_traj_setpoint.publish(sp)
        dstr = f"{dist:.1f}" if dist is not None else "?"
        self._pub_progress.publish(
            String(data=f"wp:{self._follower.wp_idx}/{len(self._follower.waypoints)} dist:{dstr}m")
        )

    def _tick(self) -> None:
        now = self.get_clock().now().nanoseconds
        period_ns = int(0.1e9) if self._daa_alert >= 1 else int(0.5e9)
        if now - self._last_pub_ns < period_ns:
            return
        self._last_pub_ns = now

        src = select_input_path(self._adjusted_path, self._global_path)
        if src is None:
            self._pub_st.publish(String(data="NO_PATH"))
            return

        if len(self._vm_data) < 8:
            self._pub_st.publish(String(data="WAITING_VEHICLE_MODEL"))
            return

        try:
            vm = vehicle_model_from_state_vector(self._vm_data)
            vm.update_weight(0.0)
        except (ValueError, IndexError):
            self._pub_st.publish(String(data="VEHICLE_MODEL_INVALID"))
            return

        wps = path_to_waypoints_nezh(src)
        cruise_param = float(self.get_parameter("cruise_speed_ms").value)
        cruise = None if cruise_param < 0.0 else cruise_param

        ok, pts, reason = build_full_path_setpoints(
            wps,
            vm,
            alert_level=self._daa_alert,
            cruise_speed_ms=cruise,
        )
        if not ok:
            self._pub_inf.publish(String(data=reason))
            self._pub_esc.publish(String(data=reason))
            self._pub_st.publish(String(data="INFEASIBLE"))
            return

        flat: List[float] = []
        for row in pts:
            flat.extend(row)
        m = Float64MultiArray()
        m.data = flat
        self._pub_sp.publish(m)
        self._pub_st.publish(String(data="OK"))
        self._pub_inf.publish(String(data=""))


def main(args: Any = None) -> int:
    rclpy.init(args=args)
    node = TrajectoryGenNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0
