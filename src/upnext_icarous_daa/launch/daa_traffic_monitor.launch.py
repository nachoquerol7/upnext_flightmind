"""ICAROUS TrafficMonitor + DAA config (requires px4_msgs in underlay, e.g. ros2_ws)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('upnext_icarous_daa')
    cfg = os.path.join(pkg, 'config', 'upnext_daa_default.txt')

    return LaunchDescription(
        [
            Node(
                package='upnext_icarous_daa',
                executable='daa_traffic_monitor_node',
                name='daa_traffic_monitor',
                output='screen',
                parameters=[
                    {'daa_config_file': cfg},
                    {'intruder_enable': True},
                    {'intruder_n_m': 80.0},
                    {'intruder_e_m': 0.0},
                ],
            ),
        ]
    )
