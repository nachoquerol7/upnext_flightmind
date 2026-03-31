"""Comprueba si la posición global PX4 cae dentro de polígonos restringidos."""

from __future__ import annotations

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, String

from px4_msgs.msg import VehicleGlobalPosition

from upnext_airspace.geo_utils import point_in_polygon_ll
from upnext_airspace.geojson_loader import centroid_deg, load_zones


class AirspaceMonitorNode(Node):
    def __init__(self) -> None:
        super().__init__('airspace_monitor')

        self.declare_parameter('geojson_path', '')
        self.declare_parameter('origin_lat_deg', 0.0)
        self.declare_parameter('origin_lon_deg', 0.0)
        self.declare_parameter('use_centroid_origin', True)
        self.declare_parameter('topic_vehicle_global', '/fmu/out/vehicle_global_position')

        path = self.get_parameter('geojson_path').get_parameter_value().string_value
        if not path.strip():
            raise RuntimeError('Param geojson_path vacío')

        self._zones = load_zones(path)
        lat0 = float(self.get_parameter('origin_lat_deg').value)
        lon0 = float(self.get_parameter('origin_lon_deg').value)
        if self.get_parameter('use_centroid_origin').value:
            lat0, lon0 = centroid_deg(self._zones)
        self._olat = lat0
        self._olon = lon0

        self._sub = self.create_subscription(
            VehicleGlobalPosition,
            self.get_parameter('topic_vehicle_global').value,
            self._on_global,
            rclpy.qos.qos_profile_sensor_data,
        )
        self._pub_in = self.create_publisher(Bool, '~/in_restricted_zone', 10)
        self._pub_detail = self.create_publisher(String, '~/restricted_zone_id', 10)
        self._last_warn = self.get_clock().now()
        self._last_hit = False

        self.get_logger().info(
            f'Monitor: {len(self._zones)} zonas, origen lat={self._olat:.6f} lon={self._olon:.6f}'
        )

    def _on_global(self, msg: VehicleGlobalPosition) -> None:
        if not msg.lat_lon_valid:
            return
        lat = float(msg.lat)
        lon = float(msg.lon)
        alt = float(msg.alt)

        hit = False
        hit_id = ''
        for z in self._zones:
            if point_in_polygon_ll(lat, lon, z.ring_ll, self._olat, self._olon):
                if z.floor_m <= alt <= z.ceiling_m:
                    hit = True
                    hit_id = z.zone_id
                    break

        b = Bool()
        b.data = hit
        self._pub_in.publish(b)
        s = String()
        s.data = hit_id if hit else ''
        self._pub_detail.publish(s)

        now = self.get_clock().now()
        if hit and (not self._last_hit or (now - self._last_warn).nanoseconds > 2e9):
            self.get_logger().warning(f'En zona restringida: {hit_id} alt={alt:.1f} m')
            self._last_warn = now
        self._last_hit = hit


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AirspaceMonitorNode()
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
