"""Puente PX4: TrajectorySetpoint solo cuando RA activa."""

from __future__ import annotations

import math
from typing import Any

from acas_node.acas_logic import AcasDecision, OwnshipState


def build_trajectory_setpoint(
    own: OwnshipState,
    dec: AcasDecision,
    stamp_us: int,
) -> Any:
    from px4_msgs.msg import TrajectorySetpoint

    nanv = float("nan")
    msg = TrajectorySetpoint()
    msg.timestamp = stamp_us
    msg.position = [float(own.n_m), float(own.e_m), float(own.z_ned_m)]
    msg.velocity = [nanv, nanv, float(-dec.climb_rate_mps)]
    msg.acceleration = [nanv, nanv, nanv]
    msg.jerk = [nanv, nanv, nanv]
    own_yaw = math.atan2(own.ve_mps, own.vn_mps)
    msg.yaw = float(
        math.atan2(
            math.sin(own_yaw + math.radians(dec.heading_delta_deg)),
            math.cos(own_yaw + math.radians(dec.heading_delta_deg)),
        )
    )
    msg.yawspeed = nanv
    return msg


def emit_acas_outputs(
    pub_traj: Any,
    own: OwnshipState,
    dec: AcasDecision,
    stamp_us: int,
) -> None:
    if not dec.ra_active:
        return
    pub_traj.publish(build_trajectory_setpoint(own, dec, stamp_us))
