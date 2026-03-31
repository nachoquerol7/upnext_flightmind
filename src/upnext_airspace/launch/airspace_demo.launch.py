"""Visualización + monitor de zonas restringidas (GeoJSON). Requiere px4_msgs en underlay para el monitor."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('upnext_airspace')
    geo = os.path.join(pkg, 'config', 'restricted_zones_sample.geojson')

    return LaunchDescription(
        [
            Node(
                package='upnext_airspace',
                executable='airspace_viz_node',
                name='airspace_viz',
                output='screen',
                parameters=[
                    {'geojson_path': geo},
                    {'use_centroid_origin': True},
                    {'frame_id': 'map'},
                    {'align_px4_ned_xy': True},
                    {'publish_hz': 1.0},
                ],
            ),
            Node(
                package='upnext_airspace',
                executable='airspace_monitor_node',
                name='airspace_monitor',
                output='screen',
                parameters=[
                    {'geojson_path': geo},
                    {'use_centroid_origin': True},
                    {'topic_vehicle_global': '/fmu/out/vehicle_global_position'},
                ],
            ),
        ]
    )
