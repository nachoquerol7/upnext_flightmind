"""Smoke / SITL demo: FSM + GPP + trajectory_gen + navigation_bridge + quality relay.

PX4 SITL y Micro XRCE-DDS Agent deben estar activos fuera de este launch.

Calidad hacia el FSM: navigation_bridge publica solo /navigation/state; el relay
navigation_quality_relay_node reenvía quality_flag a /fsm/in/quality_flag.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    include_rosbridge = LaunchConfiguration("include_rosbridge")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "include_rosbridge",
                default_value="false",
                description="Si true, arranca rosbridge_server (testbench WebSocket).",
            ),
            Node(
                package="mission_fsm",
                executable="mission_fsm_node",
                name="mission_fsm_node",
                output="screen",
                parameters=[
                    {
                        "offboard_heartbeat_hz": 10.0,
                        "offboard_enable": True,
                    }
                ],
            ),
            Node(
                package="mission_fsm",
                executable="navigation_quality_relay_node",
                name="navigation_quality_relay",
                output="screen",
            ),
            Node(
                package="gpp",
                executable="gpp_node",
                name="gpp_node",
                output="screen",
            ),
            Node(
                package="trajectory_gen",
                executable="trajectory_gen_node",
                name="trajectory_gen_node",
                output="screen",
                parameters=[
                    {
                        "use_waypoint_follower": True,
                        "use_pure_pursuit": True,
                        "pure_pursuit_lookahead_m": 2.5,
                        "path_resample_step_m": 0.6,
                        "follower_cruise_ms": 8.0,
                        "publish_px4_trajectory_setpoint": True,
                    }
                ],
            ),
            Node(
                package="navigation_bridge",
                executable="navigation_bridge_node",
                name="navigation_bridge_node",
                output="screen",
            ),
            Node(
                package="rosbridge_server",
                executable="rosbridge_websocket",
                name="rosbridge_websocket",
                output="screen",
                condition=IfCondition(include_rosbridge),
            ),
        ]
    )
