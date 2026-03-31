"""PX4 SITL (VTOL por defecto) + nodo puente ICAROUS."""

import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    bringup_share = get_package_share_directory('upnext_bringup')
    px4_launch = os.path.join(bringup_share, 'launch', 'px4_sitl.launch.py')

    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(px4_launch),
            ),
            Node(
                package='upnext_icarous_bridge',
                executable='icarous_bridge_node',
                name='icarous_bridge',
                output='screen',
                parameters=[{'publish_hz': 0.2}],
            ),
        ]
    )
