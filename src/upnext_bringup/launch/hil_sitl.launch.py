"""
HIL mínimo: PX4 SITL headless + Micro XRCE-DDS Agent + nodos ROS2 del stack (delays 2 s entre procesos).
"""

from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _hil(context, *_args, **_kwargs):
    px4_root = os.path.expanduser(LaunchConfiguration("px4_dir").perform(context))
    px4_bin = os.path.join(px4_root, "build", "px4_sitl_default", "bin", "px4")
    xrce = LaunchConfiguration("microxrce_agent").perform(context)

    mission_share = get_package_share_directory("mission_fsm")
    vtol_cfg = os.path.join(mission_share, "config", "mission_fsm_vtol.yaml")

    acas_share = get_package_share_directory("acas_node")
    acas_cfg = os.path.join(acas_share, "config", "acas.yaml")

    out: list = []

    if os.path.isfile(px4_bin):
        out.append(
            ExecuteProcess(
                cmd=[px4_bin, "-s", "etc/init.d-posix/rcS"],
                cwd=px4_root,
                output="screen",
                shell=False,
            )
        )
    else:
        out.append(
            LogInfo(
                msg=f"[hil_sitl] PX4 binary not found at {px4_bin} — skipping PX4 (SIL-only)."
            )
        )

    out.append(
        TimerAction(
            period=2.0,
            actions=[
                ExecuteProcess(
                    cmd=[xrce, "udp4", "-p", "8888"],
                    output="screen",
                    shell=False,
                )
            ],
        )
    )

    out.append(
        TimerAction(
            period=4.0,
            actions=[
                Node(
                    package="navigation_bridge",
                    executable="navigation_bridge_node",
                    name="navigation_bridge_node",
                    output="screen",
                )
            ],
        )
    )

    out.append(
        TimerAction(
            period=6.0,
            actions=[
                Node(
                    package="mission_fsm",
                    executable="mission_fsm_node",
                    name="mission_fsm_node",
                    output="screen",
                    parameters=[{"config_file": vtol_cfg}],
                )
            ],
        )
    )

    out.append(
        TimerAction(
            period=8.0,
            actions=[
                Node(
                    package="acas_node",
                    executable="acas_node",
                    name="acas_node",
                    output="screen",
                    parameters=[acas_cfg],
                )
            ],
        )
    )

    return out


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "px4_dir",
                default_value=os.path.expanduser("~/PX4-Autopilot"),
                description="Raíz del clon PX4-Autopilot (contiene build/.../bin/px4).",
            ),
            DeclareLaunchArgument(
                "microxrce_agent",
                default_value="MicroXRCEAgent",
                description="Ejecutable del agente Micro XRCE-DDS (PATH).",
            ),
            OpaqueFunction(function=_hil),
        ]
    )
