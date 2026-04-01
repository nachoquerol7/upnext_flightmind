"""Local replanner ROS 2 node: triggers, FL/path adjustments, FDIR escalation."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from typing import Any, List, Optional, Tuple

import rclpy
from geometry_msgs.msg import PoseStamped, Quaternion
from nav_msgs.msg import Path
from rclpy.node import Node
from std_msgs.msg import Bool, Float64, Float64MultiArray, Int32, String

from local_replanner.replan_core import (
    clamp_fl_delta_by_climb_rate,
    cross_track_deviation_m,
    daidalus_advisory_feasible,
    delta_fl_for_quality,
    emergency_waypoint_ne,
    parse_emergency_landing_json,
    vehicle_model_from_state_vector,
)
from local_replanner.trigger_monitor import TriggerSnapshot, select_active_trigger


def _yaw_to_quat(yaw: float) -> Quaternion:
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class LocalReplannerNode(Node):
    def __init__(self) -> None:
        super().__init__("local_replanner_node")
        self.declare_parameter("w1", 1.0)
        self.declare_parameter("w2", 1.0)
        self.declare_parameter("w3", 0.5)
        self.declare_parameter("qf_threshold", 0.65)
        self.declare_parameter("track_deviation_threshold_m", 80.0)
        self.declare_parameter("terrain_max_m", 500.0)
        self.declare_parameter("replan_dt_s", 0.5)
        self.declare_parameter("ref_lat_deg", 40.0)
        self.declare_parameter("ref_lon_deg", -3.0)
        self.declare_parameter("ref_n_m", 0.0)
        self.declare_parameter("ref_e_m", 0.0)

        self._quality = 1.0
        self._viol_imminent = False
        self._daa_alert = 0
        self._ra = [0.0, 0.0, 0.0]
        self._fl = 35.0
        self._global_path: Optional[Path] = None
        self._emergency_json = ""
        self._vm_state: List[float] = []
        self._own_n = self._own_e = 0.0
        self._adjusted_fl = 35.0

        self._pub_fl = self.create_publisher(Float64, "/local_replanner/adjusted_fl", 10)
        self._pub_path = self.create_publisher(Path, "/local_replanner/adjusted_path", 10)
        self._pub_path_exec = self.create_publisher(Path, "/local_replanner/path", 10)
        self._pub_repl_status = self.create_publisher(Bool, "/local_replanner/status", 10)
        self._pub_trig = self.create_publisher(String, "/local_replanner/active_trigger", 10)
        self._pub_fdir = self.create_publisher(String, "/fdir/active_fault", 10)

        self.create_subscription(Float64, "/nav/quality_flag", self._on_qf, 10)
        self.create_subscription(Float64MultiArray, "/ownship/state", self._on_own, 10)
        self.create_subscription(Bool, "/polycarp/violation_imminent", self._on_poly, 10)
        self.create_subscription(Int32, "/daidalus/alert_level", self._on_daa, 10)
        self.create_subscription(Float64MultiArray, "/daidalus/resolution_advisory", self._on_ra, 10)
        self.create_subscription(Float64, "/gpp/assigned_fl", self._on_fl, 10)
        self.create_subscription(Path, "/gpp/global_path", self._on_path, 10)
        self.create_subscription(Path, "/gpp/path", self._on_path, 10)
        self.create_subscription(Bool, "/local_replanner/trigger", self._on_manual_trigger, 10)
        self.create_subscription(String, "/fdir/emergency_landing_target", self._on_emg, 10)
        self.create_subscription(Float64MultiArray, "/vehicle_model/state", self._on_vm, 10)

        self.create_timer(0.2, self._tick)
        self.get_logger().info("local_replanner_node started")

    def _on_qf(self, msg: Float64) -> None:
        self._quality = float(msg.data)

    def _on_own(self, msg: Float64MultiArray) -> None:
        if len(msg.data) >= 2:
            self._own_n = float(msg.data[0])
            self._own_e = float(msg.data[1])

    def _on_poly(self, msg: Bool) -> None:
        self._viol_imminent = bool(msg.data)

    def _on_daa(self, msg: Int32) -> None:
        self._daa_alert = int(msg.data)

    def _on_ra(self, msg: Float64MultiArray) -> None:
        d = list(msg.data) + [0.0, 0.0, 0.0]
        self._ra = [float(d[0]), float(d[1]), float(d[2])]

    def _on_fl(self, msg: Float64) -> None:
        v = float(msg.data)
        if math.isfinite(v):
            self._fl = v
            self._adjusted_fl = v

    def _on_path(self, msg: Path) -> None:
        self._global_path = msg

    def _on_emg(self, msg: String) -> None:
        self._emergency_json = msg.data

    def _on_vm(self, msg: Float64MultiArray) -> None:
        self._vm_state = [float(x) for x in msg.data]

    def _on_manual_trigger(self, msg: Bool) -> None:
        if bool(msg.data):
            self._daa_alert = max(self._daa_alert, 2)

    def _blank_path(self) -> Path:
        p = Path()
        p.header.stamp = self.get_clock().now().to_msg()
        p.header.frame_id = "map"
        return p

    def _base_path(self) -> Path:
        if self._global_path is not None and self._global_path.poses:
            out = deepcopy(self._global_path)
            out.header.stamp = self.get_clock().now().to_msg()
            return out
        return self._blank_path()

    def _path_ne(self) -> List[Tuple[float, float]]:
        if self._global_path is None or not self._global_path.poses:
            return []
        return [(float(ps.pose.position.x), float(ps.pose.position.y)) for ps in self._global_path.poses]

    def _tick(self) -> None:
        qth = float(self.get_parameter("qf_threshold").get_parameter_value().double_value)
        trk_th = float(self.get_parameter("track_deviation_threshold_m").get_parameter_value().double_value)
        dt_s = float(self.get_parameter("replan_dt_s").get_parameter_value().double_value)

        path_ne = self._path_ne()
        dev = cross_track_deviation_m(self._own_n, self._own_e, path_ne)

        snap = TriggerSnapshot(
            emergency_json=self._emergency_json,
            daidalus_alert=self._daa_alert,
            violation_imminent=self._viol_imminent,
            quality_flag=self._quality,
            qf_threshold=qth,
            track_deviation_m=dev,
            track_threshold_m=trk_th,
        )
        trig = select_active_trigger(snap)
        self._pub_trig.publish(String(data=trig if trig else "NONE"))

        out_path = self._base_path()
        base_fl = self._adjusted_fl if math.isfinite(self._adjusted_fl) else self._fl

        vm = None
        if len(self._vm_state) >= 8:
            try:
                vm = vehicle_model_from_state_vector(self._vm_state)
                vm.update_weight(0.0)
            except (ValueError, IndexError):
                vm = None

        if trig is None:
            self._pub_path.publish(out_path)
            self._pub_fl.publish(Float64(data=base_fl))
            self._pub_repl_status.publish(Bool(data=False))
            return

        if trig == "EMERGENCY":
            try:
                d = parse_emergency_landing_json(self._emergency_json)
            except (json.JSONDecodeError, ValueError):
                d = {}
            en, ee = emergency_waypoint_ne(
                d,
                self._own_n,
                self._own_e,
                ref_lat_deg=float(self.get_parameter("ref_lat_deg").get_parameter_value().double_value),
                ref_lon_deg=float(self.get_parameter("ref_lon_deg").get_parameter_value().double_value),
                ref_n_m=float(self.get_parameter("ref_n_m").get_parameter_value().double_value),
                ref_e_m=float(self.get_parameter("ref_e_m").get_parameter_value().double_value),
            )
            wp = PoseStamped()
            wp.header = out_path.header
            wp.pose.position.x = en
            wp.pose.position.y = ee
            wp.pose.position.z = 0.0
            brg = math.atan2(ee - self._own_e, en - self._own_n + 1e-9)
            wp.pose.orientation = _yaw_to_quat(brg)
            out_path.poses = [wp] + list(out_path.poses)

        elif trig == "DAIDALUS" and vm is not None:
            hdg_deg, gs, vs = self._ra[0], self._ra[1], self._ra[2]
            if daidalus_advisory_feasible(vm, gs, vs):
                wp = PoseStamped()
                wp.header = out_path.header
                brg = math.radians(hdg_deg)
                wp.pose.position.x = self._own_n + 400.0 * math.cos(brg)
                wp.pose.position.y = self._own_e + 400.0 * math.sin(brg)
                wp.pose.position.z = 0.0
                wp.pose.orientation = _yaw_to_quat(brg)
                out_path.poses = [wp] + list(out_path.poses)
            else:
                self._pub_fdir.publish(String(data="LOCAL_DAA_INFEASIBLE"))

        elif trig == "GEOFENCE" and out_path.poses:
            p0 = out_path.poses[0]
            np0 = PoseStamped()
            np0.header = out_path.header
            np0.pose.position.x = float(p0.pose.position.x)
            np0.pose.position.y = float(p0.pose.position.y) + 80.0
            np0.pose.position.z = float(p0.pose.position.z)
            np0.pose.orientation = p0.pose.orientation
            out_path.poses = [np0] + list(out_path.poses[1:])

        elif trig == "QUALITY_FL" and vm is not None:
            prop = base_fl + delta_fl_for_quality(self._quality)
            self._adjusted_fl = clamp_fl_delta_by_climb_rate(base_fl, prop, vm.climb_rate_max_ms, dt_s)

        elif trig == "TRACK_DEVIATION" and len(out_path.poses) > 1:
            out_path.poses = list(out_path.poses[1:])

        self._pub_path.publish(out_path)
        self._pub_fl.publish(Float64(data=self._adjusted_fl))
        self._pub_repl_status.publish(Bool(data=True))
        self._pub_path_exec.publish(out_path)


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = LocalReplannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
