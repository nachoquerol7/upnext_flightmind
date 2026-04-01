"""FDIR ROS 2 node: detectors, policies, emergency zone JSON."""

from __future__ import annotations

import os
from typing import Any, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float64, String

from fdir.fdir_core import FdirEngine, FdirSnapshot, config_from_yaml_root, load_fdir_yaml

try:
    from ament_index_python.packages import get_package_share_directory
except ImportError:  # pragma: no cover
    get_package_share_directory = None  # type: ignore[misc, assignment]

try:
    from px4_msgs.msg import VehicleAttitudeSetpoint, VehicleImu, VehicleStatus
except ImportError:  # pragma: no cover
    VehicleImu = None  # type: ignore[misc, assignment]
    VehicleStatus = None  # type: ignore[misc, assignment]
    VehicleAttitudeSetpoint = None  # type: ignore[misc, assignment]


class FdirNode(Node):
    def __init__(self) -> None:
        super().__init__("fdir_node")

        self.declare_parameter("config_file", "")
        for key, val in (
            ("nav_mild_below", 0.65),
            ("nav_severe_below", 0.35),
            ("nav_critical_below", 0.15),
            ("motor_loss_window_s", 2.0),
            ("motor_loss_throttle_min", 0.35),
            ("motor_loss_vertical_accel_max_m_s2", -1.5),
            ("sensor_timeout_nav_quality_s", 3.0),
            ("c2_heartbeat_timeout_s", 1.5),
            ("link_loss_hold_s", 30.0),
            ("link_loss_land_s", 120.0),
            ("glide_ratio", 18.0),
            ("vehicle_lat", 40.0),
            ("vehicle_lon", -3.0),
            ("vehicle_altitude_amsl_m", 2000.0),
        ):
            self.declare_parameter(key, val)

        cfg_path = self.get_parameter("config_file").get_parameter_value().string_value.strip()
        if cfg_path and os.path.isfile(cfg_path):
            path = cfg_path
        else:
            if get_package_share_directory is None:
                raise RuntimeError("ament_index_python required for default FDIR config")
            path = os.path.join(get_package_share_directory("fdir"), "config", "fdir.yaml")
            if not os.path.isfile(path):
                raise FileNotFoundError(f"FDIR config not found: {path}")

        root = load_fdir_yaml(path)
        ros_params = root.setdefault("fdir_node", {}).setdefault("ros__parameters", {})
        for p in (
            "nav_mild_below",
            "nav_severe_below",
            "nav_critical_below",
            "motor_loss_window_s",
            "motor_loss_throttle_min",
            "motor_loss_vertical_accel_max_m_s2",
            "sensor_timeout_nav_quality_s",
            "c2_heartbeat_timeout_s",
            "link_loss_hold_s",
            "link_loss_land_s",
            "glide_ratio",
            "vehicle_lat",
            "vehicle_lon",
            "vehicle_altitude_amsl_m",
        ):
            ros_params[p] = self.get_parameter(p).get_parameter_value().double_value
        self._engine = FdirEngine(config_from_yaml_root(root))

        self._quality: Optional[float] = None
        self._last_quality_rx: Optional[float] = None
        self._c2_last_rx: Optional[float] = None
        self._fsm_mode: str = "PREFLIGHT"
        self._throttle_cmd: float = 0.0
        self._vert_accel: float = 0.0
        self._armed: bool = False
        self._failure_motor: bool = False

        self._pub_fault = self.create_publisher(String, "/fdir/active_fault", 10)
        self._pub_policy = self.create_publisher(String, "/fdir/policy_action", 10)
        self._pub_zone = self.create_publisher(String, "/fdir/emergency_landing_target", 10)

        self.create_subscription(Float64, "/nav/quality_flag", self._on_quality, 10)
        self.create_subscription(String, "/fsm/current_mode", self._on_fsm, 10)
        self.create_subscription(Bool, "/fdir/in/c2_heartbeat", self._on_c2, 10)

        if VehicleImu is None or VehicleStatus is None or VehicleAttitudeSetpoint is None:
            raise RuntimeError("px4_msgs is required (VehicleImu, VehicleStatus, VehicleAttitudeSetpoint)")

        self.create_subscription(VehicleImu, "/fmu/out/vehicle_imu", self._on_imu, 10)
        self.create_subscription(VehicleStatus, "/fmu/out/vehicle_status", self._on_status, 10)
        self.create_subscription(
            VehicleAttitudeSetpoint,
            "/fmu/out/vehicle_attitude_setpoint",
            self._on_att_sp,
            10,
        )

        self.create_timer(0.05, self._tick)
        self.get_logger().info(f"FDIR node started (config {path})")

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_quality(self, msg: Float64) -> None:
        self._quality = float(msg.data)
        self._last_quality_rx = self._now()

    def _on_fsm(self, msg: String) -> None:
        self._fsm_mode = msg.data

    def _on_c2(self, _msg: Bool) -> None:
        self._c2_last_rx = self._now()

    def _on_imu(self, msg: Any) -> None:
        dt = max(1e-6, float(msg.delta_velocity_dt) / 1e6)
        dvz = float(msg.delta_velocity[2])
        az_down = dvz / dt
        self._vert_accel = float(-az_down)

    def _on_status(self, msg: Any) -> None:
        self._armed = int(msg.arming_state) == 2
        self._failure_motor = (int(msg.failure_detector_status) & 128) != 0

    def _on_att_sp(self, msg: Any) -> None:
        tb = msg.thrust_body
        self._throttle_cmd = max(0.0, min(1.0, float(tb[0])))

    def _tick(self) -> None:
        now = self._now()
        lat = float(self.get_parameter("vehicle_lat").get_parameter_value().double_value)
        lon = float(self.get_parameter("vehicle_lon").get_parameter_value().double_value)
        alt = float(self.get_parameter("vehicle_altitude_amsl_m").get_parameter_value().double_value)

        snap = FdirSnapshot(
            time_sec=now,
            quality_flag=self._quality,
            last_quality_rx_time=self._last_quality_rx,
            c2_heartbeat_last_rx=self._c2_last_rx,
            throttle_commanded=self._throttle_cmd,
            vertical_accel_m_s2=self._vert_accel,
            armed=self._armed,
            failure_motor_px4=self._failure_motor,
            fsm_mode=self._fsm_mode,
            vehicle_lat=lat,
            vehicle_lon=lon,
            vehicle_altitude_amsl_m=alt,
        )
        out = self._engine.evaluate(snap)
        self._pub_fault.publish(String(data=out.active_fault))
        self._pub_policy.publish(String(data=out.policy_action))
        self._pub_zone.publish(String(data=out.emergency_landing_target_json))


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = FdirNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
