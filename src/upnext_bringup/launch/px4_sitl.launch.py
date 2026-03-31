"""
PX4 SITL with Gazebo (gz): default vehicle is standard VTOL (not multicopter).

Override with: vehicle:=gz_x500  (quad) or see PX4 docs for other gz_* targets.

Requires: PX4-Autopilot built for simulation, Gazebo Harmonic (gz) per PX4 docs.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def _launch_px4(context, *_args, **_kwargs):
    px4_dir = LaunchConfiguration('px4_dir').perform(context)
    vehicle = LaunchConfiguration('vehicle').perform(context)
    px4_dir = os.path.expanduser(px4_dir)
    if not os.path.isdir(px4_dir):
        raise FileNotFoundError(
            f'PX4-Autopilot not found at {px4_dir}. Set px4_dir or clone PX4.'
        )
    return [
        ExecuteProcess(
            cmd=['make', '-C', px4_dir, 'px4_sitl', vehicle],
            output='screen',
            shell=False,
        )
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'px4_dir',
                default_value=os.path.expanduser('~/PX4-Autopilot'),
                description='Absolute path to PX4-Autopilot clone.',
            ),
            DeclareLaunchArgument(
                'vehicle',
                default_value='gz_standard_vtol',
                description=(
                    'PX4 gz SITL target, e.g. gz_standard_vtol (default), gz_x500, gz_plane'
                ),
            ),
            OpaqueFunction(function=_launch_px4),
        ]
    )
