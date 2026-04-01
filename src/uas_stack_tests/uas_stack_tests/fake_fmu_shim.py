"""Publica topics mínimos /fmu/out/* para que fdir_node arranque sin PX4 real."""

from __future__ import annotations

from typing import Any

import rclpy
from rclpy.node import Node


class FakeFmuShim(Node):
    def __init__(self) -> None:
        super().__init__("fake_fmu_shim")
        from px4_msgs.msg import VehicleAttitudeSetpoint, VehicleImu, VehicleStatus

        self._pub_imu = self.create_publisher(VehicleImu, "/fmu/out/vehicle_imu", 10)
        self._pub_st = self.create_publisher(VehicleStatus, "/fmu/out/vehicle_status", 10)
        self._pub_att = self.create_publisher(
            VehicleAttitudeSetpoint, "/fmu/out/vehicle_attitude_setpoint", 10
        )
        self._us = 0
        self.create_timer(0.05, self._tick)
        self.get_logger().info("fake_fmu_shim: IMU + status + attitude_setpoint (SIL)")

    def _tick(self) -> None:
        from px4_msgs.msg import VehicleAttitudeSetpoint, VehicleImu, VehicleStatus

        self._us += 50_000
        imu = VehicleImu()
        imu.timestamp = self._us
        imu.timestamp_sample = self._us
        imu.delta_velocity_dt = 5_000
        imu.delta_velocity = [0.0, 0.0, 0.0]
        imu.delta_angle_dt = 5_000
        imu.delta_angle = [0.0, 0.0, 0.0]
        self._pub_imu.publish(imu)

        st = VehicleStatus()
        st.timestamp = self._us
        st.arming_state = 1
        if hasattr(st, "failure_detector_status"):
            st.failure_detector_status = 0
        self._pub_st.publish(st)

        att = VehicleAttitudeSetpoint()
        att.timestamp = self._us
        att.thrust_body = [0.25, 0.0, 0.0]
        att.q_d = [1.0, 0.0, 0.0, 0.0]
        self._pub_att.publish(att)


def main(args: Any = None) -> int:
    rclpy.init(args=args)
    node = FakeFmuShim()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0
