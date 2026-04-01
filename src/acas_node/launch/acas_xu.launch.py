"""ACAS Xu node with optional SCHED_FIFO (chrt); requires Linux RT privileges."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share = get_package_share_directory("acas_node")
    cfg = os.path.join(share, "config", "acas.yaml")
    return LaunchDescription(
        [
            Node(
                package="acas_node",
                executable="acas_node",
                name="acas_node",
                output="screen",
                parameters=[cfg],
            ),
        ]
    )
