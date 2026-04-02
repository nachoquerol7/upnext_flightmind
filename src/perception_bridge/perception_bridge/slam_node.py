"""Nodo SLAM: integración inercial + proxy de calidad desde nube (backend FAST-LIO2 vía parámetro)."""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, PointCloud2
from std_msgs.msg import Float64

from perception_bridge.point_cloud_utils import (
    list_xyz_points,
    mean_distance_to_centroid,
    pointcloud2_from_xyz,
)


def quality_flag_from_cov_proxy(c0: float) -> float:
    """Mismos umbrales que navigation_bridge._quality_from_cov (varianza proxy ≥ 0)."""
    c0 = max(0.0, float(c0))
    if c0 > 5.0:
        return 0.3
    if c0 > 1.0:
        return 0.7
    return 1.0


def _quat_normalize(q: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in q)) or 1.0
    return [x / n for x in q]


def _quat_mul(a: list[float], b: list[float]) -> list[float]:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return [
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ]


def _rotate_vec_by_quat(v: list[float], q: list[float]) -> list[float]:
    """R(q) * v; q = [w,x,y,z] unit."""
    w, x, y, z = q
    vx, vy, vz = v
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return [
        vx + w * tx + y * tz - z * ty,
        vy + w * ty + z * tx - x * tz,
        vz + w * tz + x * ty - y * tx,
    ]


class SlamNode(Node):
    def __init__(self) -> None:
        super().__init__("slam_node")
        self.declare_parameter("slam_backend", "stub")
        self.declare_parameter("initial_pose_x", 0.0)
        self.declare_parameter("initial_pose_y", 0.0)
        self.declare_parameter("initial_pose_z", 100.0)
        self.declare_parameter("pose_covariance_diag", [1e-2, 1e-2, 1e-2, 1e-3, 1e-3, 1e-3])
        self.declare_parameter("scan_var_scale", 8.0)
        self.declare_parameter("scan_density_ref", 400.0)

        self._sub_scan = self.create_subscription(
            PointCloud2, "/scan", self._on_scan, qos_profile_sensor_data
        )
        self._sub_imu = self.create_subscription(
            Imu, "/imu/data", self._on_imu, qos_profile_sensor_data
        )

        self._pub_pose = self.create_publisher(PoseWithCovarianceStamped, "/slam/pose", 10)
        self._pub_quality = self.create_publisher(Float64, "/slam/quality", 10)
        self._pub_map = self.create_publisher(PointCloud2, "/slam/map", 10)
        self._pub_nav_override = self.create_publisher(Float64, "/nav/quality_override", 10)

        self._timer = self.create_timer(1.0 / 50.0, self._tick_50hz)

        ix = float(self.get_parameter("initial_pose_x").value)
        iy = float(self.get_parameter("initial_pose_y").value)
        iz = float(self.get_parameter("initial_pose_z").value)
        self._p = [ix, iy, iz]
        self._v = [0.0, 0.0, 0.0]
        self._q = [1.0, 0.0, 0.0, 0.0]
        self._last_imu: Imu | None = None
        self._last_cloud_pts: list[tuple[float, float, float]] = []
        self._slam_quality_continuous = 0.3
        self._cov_proxy = 10.0

    def _on_scan(self, msg: PointCloud2) -> None:
        pts = list_xyz_points(msg)
        self._last_cloud_pts = pts
        n = len(pts)
        scale = float(self.get_parameter("scan_var_scale").value)
        dens_ref = float(self.get_parameter("scan_density_ref").value)
        if n == 0:
            self._slam_quality_continuous = 0.3
            self._cov_proxy = 10.0
            return
        md = mean_distance_to_centroid(pts)
        dens = min(1.0, n / dens_ref)
        self._slam_quality_continuous = float(0.3 + 0.7 * min(1.0, dens * math.exp(-md / 4.0)))
        self._cov_proxy = max(1e-6, (md * md) * scale / max(0.15, dens))

    def _on_imu(self, msg: Imu) -> None:
        self._last_imu = msg

    def _integrate_imu(self, dt: float) -> None:
        imu = self._last_imu
        if imu is None or dt <= 0.0:
            return
        wx = float(imu.angular_velocity.x)
        wy = float(imu.angular_velocity.y)
        wz = float(imu.angular_velocity.z)
        omega_q = [0.0, wx, wy, wz]
        q = self._q
        qd = _quat_mul(q, omega_q)
        self._q = _quat_normalize(
            [q[i] + 0.5 * dt * qd[i] for i in range(4)]
        )

        ax = float(imu.linear_acceleration.x)
        ay = float(imu.linear_acceleration.y)
        az = float(imu.linear_acceleration.z)
        g_world = [0.0, 0.0, 9.81]
        acc_world = _rotate_vec_by_quat([ax, ay, az], self._q)
        awx = acc_world[0] - g_world[0]
        awy = acc_world[1] - g_world[1]
        awz = acc_world[2] - g_world[2]
        self._v[0] += awx * dt
        self._v[1] += awy * dt
        self._v[2] += awz * dt
        self._p[0] += self._v[0] * dt
        self._p[1] += self._v[1] * dt
        self._p[2] += self._v[2] * dt

    def _tick_50hz(self) -> None:
        backend = str(self.get_parameter("slam_backend").value)
        if backend != "stub":
            self.get_logger().warn(
                f"slam_backend='{backend}' no soportado aún; usando integración stub",
                throttle_duration_sec=5.0,
            )

        dt = 1.0 / 50.0
        self._integrate_imu(dt)

        now = self.get_clock().now().to_msg()
        qw, qx, qy, qz = self._q

        pose_msg = PoseWithCovarianceStamped()
        pose_msg.header.stamp = now
        pose_msg.header.frame_id = "map"
        pose_msg.pose.pose.position.x = float(self._p[0])
        pose_msg.pose.pose.position.y = float(self._p[1])
        pose_msg.pose.pose.position.z = float(self._p[2])
        pose_msg.pose.pose.orientation.w = float(qw)
        pose_msg.pose.pose.orientation.x = float(qx)
        pose_msg.pose.pose.orientation.y = float(qy)
        pose_msg.pose.pose.orientation.z = float(qz)

        diag = list(self.get_parameter("pose_covariance_diag").value)
        if len(diag) != 6:
            diag = [1e-2] * 6
        cov = [0.0] * 36
        for i in range(6):
            cov[i * 6 + i] = float(diag[i])
        pose_msg.pose.covariance = cov
        self._pub_pose.publish(pose_msg)

        q_cont = float(self._slam_quality_continuous)
        self._pub_quality.publish(Float64(data=q_cont))

        q_nav = quality_flag_from_cov_proxy(self._cov_proxy)
        self._pub_nav_override.publish(Float64(data=q_nav))

        px, py, pz = self._p[0], self._p[1], self._p[2]
        if self._last_cloud_pts:
            map_pts = [(px + a, py + b, pz + c) for a, b, c in self._last_cloud_pts[:2000]]
        else:
            map_pts = [(px, py, pz)]
        stub_map = pointcloud2_from_xyz(map_pts, frame_id="map")
        stub_map.header.stamp = now
        self._pub_map.publish(stub_map)


def main() -> None:
    rclpy.init()
    node = SlamNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
