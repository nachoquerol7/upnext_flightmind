"""Nodo ACAS Xu simplificado: solo ownship + tráfico; sin topics de planificación."""

from __future__ import annotations

from typing import Any, List, Optional

import rclpy
from flightmind_msgs.msg import TrafficReport
from rclpy.node import Node
from std_msgs.msg import Bool, Float64MultiArray

from acas_node.acas_fc import emit_acas_outputs
from acas_node.acas_logic import (
    AcasConfig,
    IntruderState,
    compute_acas_decision,
    ownship_from_floats,
)


def _stamp_us(node: Node) -> int:
    return int(node.get_clock().now().nanoseconds // 1000)


class AcasNode(Node):
    def __init__(self) -> None:
        super().__init__("acas_node")
        self.declare_parameter("tau_ca", 45.0)
        self.declare_parameter("dmod_ca", 1800.0)
        self.declare_parameter("z_sep_m", 120.0)
        self.declare_parameter("ra_climb_rate_mps", 3.0)
        self.declare_parameter("ra_heading_delta_deg", 30.0)
        self._cfg = AcasConfig(
            tau_ca_s=float(self.get_parameter("tau_ca").value),
            dmod_ca_m=float(self.get_parameter("dmod_ca").value),
            z_sep_m=float(self.get_parameter("z_sep_m").value),
            ra_climb_rate_mps=float(self.get_parameter("ra_climb_rate_mps").value),
            ra_heading_delta_deg=float(self.get_parameter("ra_heading_delta_deg").value),
        )

        from px4_msgs.msg import TrajectorySetpoint

        self._own: Optional[OwnshipState] = None
        self._intruders: List[IntruderState] = []

        self._pub_active = self.create_publisher(Bool, "/acas/ra_active", 10)
        self._pub_ra = self.create_publisher(Float64MultiArray, "/acas/resolution_advisory", 10)
        self._pub_traj = self.create_publisher(
            TrajectorySetpoint, "/fmu/in/trajectory_setpoint", 10
        )

        self.create_subscription(Float64MultiArray, "/ownship/state", self._on_own, 10)
        self.create_subscription(TrafficReport, "/traffic/intruders", self._on_traffic, 10)

        self.create_timer(0.05, self._tick)
        self.get_logger().info("acas_node: ACAS Xu tabla (sin planificación)")

    def _on_own(self, msg: Any) -> None:
        self._own = ownship_from_floats(msg.data)

    def _on_traffic(self, msg: Any) -> None:
        out: List[IntruderState] = []
        for i in msg.intruders:
            out.append(
                IntruderState(
                    id=int(i.id),
                    n_m=float(i.n_m),
                    e_m=float(i.e_m),
                    z_ned_m=float(i.z_ned_m),
                    vn_mps=float(i.vn_mps),
                    ve_mps=float(i.ve_mps),
                    vd_mps=float(i.vd_mps),
                )
            )
        self._intruders = out

    def _tick(self) -> None:
        if self._own is None:
            return
        dec = compute_acas_decision(self._own, self._intruders, self._cfg)
        self._pub_active.publish(Bool(data=dec.ra_active))
        ra = Float64MultiArray()
        ra.data = [float(dec.climb_rate_mps), float(dec.heading_delta_deg)]
        self._pub_ra.publish(ra)
        emit_acas_outputs(self._pub_traj, self._own, dec, _stamp_us(self))


def main(args: Any = None) -> int:
    rclpy.init(args=args)
    node = AcasNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0
