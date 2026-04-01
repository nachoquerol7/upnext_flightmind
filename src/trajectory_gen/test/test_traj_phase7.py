"""Phase 7 trajectory_gen: Dubins 3D, vehicle checks, ROS I/O."""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from nav_msgs.msg import Path
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile
from std_msgs.msg import Float64MultiArray, String

from trajectory_gen.dubins3d import (
    build_setpoints_leg,
    num_samples_for_length,
    setpoints_to_trajectory_segments,
)
from trajectory_gen.trajectory_gen_node import TrajectoryGenNode, select_input_path
from vehicle_model.model import VehicleModel


def _vm_default() -> VehicleModel:
    return VehicleModel(
        v_min_ms=28.0,
        v_max_ms=57.0,
        turn_radius_min_m=600.0,
        climb_rate_max_ms=8.0,
        descent_rate_max_ms=5.0,
        glide_ratio=18.0,
        mtow_kg=750.0,
        fuel_burn_kgh=50.0,
        fuel_mass_initial_kg=100.0,
        v_min_reserve_gain_ms=0.0,
    )


def test_dubins_respects_min_turn_radius() -> None:
    vm = _vm_default()
    vm.update_weight(0.0)
    ok, pts, reason = build_setpoints_leg(
        0.0, 0.0, 500.0, 0.0,
        5000.0, 2000.0, 500.0, 0.4,
        vm,
        alert_level=0,
    )
    assert ok, reason
    segs = setpoints_to_trajectory_segments(pts)
    assert segs
    for s in segs:
        assert s.turn_radius_m + 1e-2 >= vm.turn_radius_min_m


def test_trajectory_rejected_if_exceeds_climb_rate() -> None:
    vm = _vm_default()
    vm.update_weight(0.0)
    ok, _, reason = build_setpoints_leg(
        0.0, 0.0, 0.0, 0.0,
        150.0, 0.0, 600.0, 0.0,
        vm,
        alert_level=0,
    )
    assert not ok
    assert "climb" in reason


def test_trajectory_rejected_if_below_vmin() -> None:
    vm = _vm_default()
    vm.update_weight(0.0)
    ok, _, reason = build_setpoints_leg(
        0.0, 0.0, 100.0, 0.0,
        3000.0, 500.0, 100.0, 0.2,
        vm,
        alert_level=0,
        cruise_speed_ms=10.0,
    )
    assert not ok
    assert reason == "below_v_min"


def _two_pose_path(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> Path:
    p = Path()
    for x, y, z in ((x0, y0, z0), (x1, y1, z1)):
        ps = PoseStamped()
        ps.pose = Pose()
        ps.pose.position = Point(x=float(x), y=float(y), z=float(z))
        ps.pose.orientation = Quaternion(x=0.0, y=0.0, z=math.sin(0.15), w=math.cos(0.15))
        p.poses.append(ps)
    return p


def test_uses_adjusted_path_over_global_path() -> None:
    adj = _two_pose_path(1.0, 2.0, 0.0, 4.0, 8.0, 0.0)
    glb = _two_pose_path(100.0, 200.0, 0.0, 130.0, 220.0, 0.0)
    chosen = select_input_path(adj, glb)
    assert chosen is not None
    assert chosen.poses[0].pose.position.x == 1.0


def test_infeasible_publishes_reason() -> None:
    rclpy.init()
    latched = QoSProfile(
        depth=1,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        history=HistoryPolicy.KEEP_LAST,
    )
    received: list[str] = []

    def on_inf(msg: String) -> None:
        if msg.data:
            received.append(msg.data)

    traj = TrajectoryGenNode()
    dummy = rclpy.create_node("traj_test_pub")
    dummy.create_subscription(String, "/trajectory_gen/infeasible_reason", on_inf, 10)
    pub_vm = dummy.create_publisher(Float64MultiArray, "/vehicle_model/state", latched)
    pub_path = dummy.create_publisher(Path, "/gpp/global_path", 10)

    vm = Float64MultiArray()
    vm.data = [28.0, 57.0, 600.0, 8.0, 5.0, 18.0, 700.0, 100.0]
    pub_vm.publish(vm)
    pub_path.publish(_two_pose_path(0.0, 0.0, 0.0, 120.0, 0.0, 900.0))

    ex = SingleThreadedExecutor()
    ex.add_node(traj)
    ex.add_node(dummy)
    for _ in range(120):
        ex.spin_once(timeout_sec=0.05)
        if received:
            break

    traj.destroy_node()
    dummy.destroy_node()
    rclpy.shutdown()
    assert received
    assert "climb" in received[0]


def test_interpolation_density_increases_on_alert() -> None:
    l_m = 800.0
    n_lo = num_samples_for_length(l_m, 0)
    n_hi = num_samples_for_length(l_m, 1)
    assert n_hi > n_lo
