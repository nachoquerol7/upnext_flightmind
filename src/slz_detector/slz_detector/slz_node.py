"""SLZ: mapa SLAM en celdas 3×3 m + puntuación geométrica → candidatos NED."""

from __future__ import annotations

import json
import math
from collections import defaultdict

import rclpy
from geometry_msgs.msg import Pose, PoseArray, PoseStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, PointCloud2
from std_msgs.msg import String

from slz_detector.cloud_io import list_xyz_points
from slz_detector.terrain_classifier import TerrainClassifier

CELL_M = 3.0
CELL_AREA = CELL_M * CELL_M


class SlzNode(Node):
    def __init__(self) -> None:
        super().__init__("slz_node")
        self._classifier = TerrainClassifier()

        self._sub_image = self.create_subscription(
            Image, "/camera/image_raw", self._on_image, qos_profile_sensor_data
        )
        self._sub_map = self.create_subscription(PointCloud2, "/slam/map", self._on_map, 10)

        self._pub_candidates = self.create_publisher(PoseArray, "/slz/candidates", 10)
        self._pub_best = self.create_publisher(PoseStamped, "/slz/best", 10)
        self._pub_status = self.create_publisher(String, "/slz/status", 10)

        self._last_scored: list[tuple[float, float, float, float]] = []
        self._timer = self.create_timer(0.2, self._publish_outputs)

    def _on_image(self, msg: Image) -> None:
        _ = self._classifier.classify(msg)

    def _map_to_ned(self, mx: float, my: float, mz: float) -> tuple[float, float, float]:
        """Mapa tipo ENU (z arriba) → NED publicado (x=N, y=E, z=D)."""
        return (my, mx, -mz)

    def _on_map(self, msg: PointCloud2) -> None:
        pts = list_xyz_points(msg)
        if not pts:
            self._last_scored = []
            return

        cells: dict[tuple[int, int], list[tuple[float, float, float]]] = defaultdict(list)
        for p in pts:
            ix = int(math.floor(p[0] / CELL_M))
            iy = int(math.floor(p[1] / CELL_M))
            cells[(ix, iy)].append(p)

        scored: list[tuple[float, float, float, float, float, float, float]] = []
        for (ix, iy), cell_pts in cells.items():
            s = self._classifier.score(cell_pts, CELL_AREA)
            cx = (ix + 0.5) * CELL_M
            cy = (iy + 0.5) * CELL_M
            cz = sum(pt[2] for pt in cell_pts) / len(cell_pts)
            n, e, d = self._map_to_ned(cx, cy, cz)
            scored.append((s, n, e, d, cx, cy, cz))

        scored.sort(key=lambda t: -t[0])
        self._last_scored = scored[:3]

    def _make_pose_ned(self, n: float, e: float, d: float) -> Pose:
        p = Pose()
        p.position.x = n
        p.position.y = e
        p.position.z = d
        p.orientation.w = 1.0
        return p

    def _publish_outputs(self) -> None:
        now = self.get_clock().now().to_msg()
        arr = PoseArray()
        arr.header.stamp = now
        arr.header.frame_id = "map"
        for t in self._last_scored:
            _, n, e, d, _, _, _ = t
            arr.poses.append(self._make_pose_ned(n, e, d))
        self._pub_candidates.publish(arr)

        best = PoseStamped()
        best.header.stamp = now
        best.header.frame_id = "map"
        if self._last_scored:
            s, n, e, d, _, _, _ = self._last_scored[0]
            best.pose = self._make_pose_ned(n, e, d)
            best_score = float(s)
            best_ned = [n, e, d]
        else:
            best.pose = self._make_pose_ned(0.0, 0.0, 0.0)
            best_score = 0.0
            best_ned = [0.0, 0.0, 0.0]
        self._pub_best.publish(best)

        status = {
            "n_candidates": len(self._last_scored),
            "best_score": best_score,
            "best_ned": best_ned,
        }
        self._pub_status.publish(String(data=json.dumps(status)))


def main() -> None:
    rclpy.init()
    node = SlzNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
