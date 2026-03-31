"""PX4 SITL (VTOL) + ICAROUS TrafficMonitor (needs upnext_bringup)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    bringup_share = get_package_share_directory('upnext_bringup')
    px4_launch = os.path.join(bringup_share, 'launch', 'px4_sitl.launch.py')

    pkg = get_package_share_directory('upnext_icarous_daa')
    cfg = os.path.join(pkg, 'config', 'upnext_daa_default.txt')

    return LaunchDescription(
        [
            IncludeLaunchDescription(PythonLaunchDescriptionSource(px4_launch)),
            Node(
                package='upnext_icarous_daa',
                executable='daa_traffic_monitor_node',
                name='daa_traffic_monitor',
                output='screen',
                parameters=[
                    {'daa_config_file': cfg},
                    {'intruder_enable': True},
                    {'intruder_n_m': 80.0},
                ],
            ),
        ]
    )
