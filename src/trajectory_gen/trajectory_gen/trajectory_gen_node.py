"""Subscribe paths + vehicle state; publish discretised Dubins 3D setpoints."""

from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple

import rclpy
from geometry_msgs.msg import Quaternion
from nav_msgs.msg import Path
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile
from std_msgs.msg import Float64MultiArray, Int32, String

from trajectory_gen.dubins3d import (
    build_full_path_setpoints,
    vehicle_model_from_state_vector,
)


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

        self._pub_sp = self.create_publisher(Float64MultiArray, "/trajectory/setpoints", 10)
        self._pub_st = self.create_publisher(String, "/trajectory_gen/status", 10)
        self._pub_inf = self.create_publisher(String, "/trajectory_gen/infeasible_reason", 10)
        self._pub_esc = self.create_publisher(String, "/local_replanner/trajectory_infeasible", 10)

        self.create_subscription(Path, "/local_replanner/adjusted_path", self._on_adj, 10)
        self.create_subscription(Path, "/gpp/global_path", self._on_glob, 10)
        self.create_subscription(Float64MultiArray, "/vehicle_model/state", self._on_vm, latched)
        self.create_subscription(Int32, "/daidalus/alert_level", self._on_daa, 10)

        self.create_timer(0.05, self._tick)
        self.get_logger().info("trajectory_gen_node started (base tick 20 Hz; output throttled)")

    def _on_adj(self, msg: Path) -> None:
        self._adjusted_path = msg

    def _on_glob(self, msg: Path) -> None:
        self._global_path = msg

    def _on_vm(self, msg: Float64MultiArray) -> None:
        self._vm_data = [float(x) for x in msg.data]

    def _on_daa(self, msg: Int32) -> None:
        self._daa_alert = int(msg.data)

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
