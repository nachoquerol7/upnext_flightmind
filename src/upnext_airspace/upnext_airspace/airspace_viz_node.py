"""Publica MarkerArray (contorno + relleno + etiqueta) en frame `airspace_enu`."""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Point
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray

from upnext_airspace.geo_utils import ring_ll_to_xy
from upnext_airspace.geojson_loader import centroid_deg, load_zones


class AirspaceVizNode(Node):
    def __init__(self) -> None:
        super().__init__('airspace_viz')

        self.declare_parameter('geojson_path', '')
        self.declare_parameter('origin_lat_deg', 0.0)
        self.declare_parameter('origin_lon_deg', 0.0)
        self.declare_parameter('use_centroid_origin', True)
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('align_px4_ned_xy', True)
        self.declare_parameter('z_floor', 0.0)
        self.declare_parameter('publish_hz', 1.0)

        path = self.get_parameter('geojson_path').get_parameter_value().string_value
        if not path.strip():
            raise RuntimeError('Param geojson_path vacío (ruta al .geojson)')

        self._zones = load_zones(path)
        if not self._zones:
            self.get_logger().warn('GeoJSON sin polígonos válidos')

        lat0 = self.get_parameter('origin_lat_deg').value
        lon0 = self.get_parameter('origin_lon_deg').value
        if self.get_parameter('use_centroid_origin').value:
            lat0, lon0 = centroid_deg(self._zones)
            self.get_logger().info(f'Origen mapa (centroide zonas): lat={lat0:.6f} lon={lon0:.6f}')

        self._origin_lat = float(lat0)
        self._origin_lon = float(lon0)
        self._frame = self.get_parameter('frame_id').get_parameter_value().string_value
        self._align_px4 = self.get_parameter('align_px4_ned_xy').value
        self._z = float(self.get_parameter('z_floor').value)

        self._pub = self.create_publisher(MarkerArray, '~/markers', 10)

        hz = max(0.2, float(self.get_parameter('publish_hz').value))
        self._timer = self.create_timer(1.0 / hz, self._publish)
        self.get_logger().info(
            f'Airspace viz: {len(self._zones)} zonas desde {path} '
            f'(frame={self._frame}, align_px4_ned_xy={self._align_px4})'
        )

    def _xy_to_marker(self, x_east: float, y_north: float) -> Point:
        """Equirectangular (east,north) m -> RViz: si align, coincide con NED x=norte y=este."""
        if self._align_px4:
            return Point(x=float(y_north), y=float(x_east), z=float(self._z))
        return Point(x=float(x_east), y=float(y_north), z=float(self._z))

    def _publish(self) -> None:
        now = self.get_clock().now()
        markers: list[Marker] = []
        mid = 0

        for z in self._zones:
            poly_xy = ring_ll_to_xy(z.ring_ll, self._origin_lat, self._origin_lon)
            if len(poly_xy) < 3:
                continue

            # quitar cierre duplicado para triangulación
            ring = [tuple(p) for p in poly_xy]
            if len(ring) >= 2 and ring[0] == ring[-1]:
                ring = ring[:-1]
            n = len(ring)
            if n < 3:
                continue

            # Contorno
            line = Marker()
            line.header.frame_id = self._frame
            line.header.stamp = now.to_msg()
            line.ns = 'airspace_outline'
            line.id = mid
            mid += 1
            line.type = Marker.LINE_STRIP
            line.action = Marker.ADD
            line.scale.x = 4.0
            line.color.r = 1.0
            line.color.g = 0.2
            line.color.b = 0.1
            line.color.a = 1.0
            line.pose.orientation.w = 1.0
            for x, y in ring:
                line.points.append(self._xy_to_marker(x, y))
            line.points.append(self._xy_to_marker(ring[0][0], ring[0][1]))
            markers.append(line)

            # Relleno (abanico)
            tri = Marker()
            tri.header.frame_id = self._frame
            tri.header.stamp = now.to_msg()
            tri.ns = 'airspace_fill'
            tri.id = mid
            mid += 1
            tri.type = Marker.TRIANGLE_LIST
            tri.action = Marker.ADD
            tri.scale.x = 1.0
            tri.scale.y = 1.0
            tri.scale.z = 1.0
            tri.color.r = 1.0
            tri.color.g = 0.3
            tri.color.b = 0.1
            tri.color.a = 0.35
            tri.pose.orientation.w = 1.0
            for i in range(1, n - 1):
                for idx in (0, i, i + 1):
                    x, y = ring[idx]
                    tri.points.append(self._xy_to_marker(x, y))
            markers.append(tri)

            # Etiqueta
            cx_e = sum(p[0] for p in ring) / n
            cy_n = sum(p[1] for p in ring) / n
            ctr = self._xy_to_marker(cx_e, cy_n)
            txt = Marker()
            txt.header.frame_id = self._frame
            txt.header.stamp = now.to_msg()
            txt.ns = 'airspace_labels'
            txt.id = mid
            mid += 1
            txt.type = Marker.TEXT_VIEW_FACING
            txt.action = Marker.ADD
            txt.pose.position.x = ctr.x
            txt.pose.position.y = ctr.y
            txt.pose.position.z = float(self._z) + 15.0
            txt.pose.orientation.w = 1.0
            txt.scale.z = 12.0
            txt.color.r = 1.0
            txt.color.g = 1.0
            txt.color.b = 1.0
            txt.color.a = 1.0
            txt.text = f'{z.name}\n{z.floor_m:.0f}-{z.ceiling_m:.0f} m'
            markers.append(txt)

        msg = MarkerArray()
        msg.markers = markers
        self._pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AirspaceVizNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
