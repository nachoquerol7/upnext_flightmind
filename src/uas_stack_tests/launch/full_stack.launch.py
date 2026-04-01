"""Stack completo UpNext (SIL): shim FMU + feeds + nodos de fases 1–8."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def _share(pkg: str, *parts: str) -> str:
    return os.path.join(get_package_share_directory(pkg), *parts)


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="uas_stack_tests",
                executable="fake_fmu_shim",
                name="fake_fmu_shim",
                output="screen",
            ),
            Node(
                package="uas_stack_tests",
                executable="stack_integration_feeds",
                name="stack_integration_feeds",
                output="screen",
            ),
            Node(
                package="vehicle_model",
                executable="vehicle_model_node",
                name="vehicle_model_node",
                output="screen",
                parameters=[_share("vehicle_model", "config", "vehicle_model.yaml")],
            ),
            Node(
                package="mission_fsm",
                executable="mission_fsm_node",
                name="mission_fsm_node",
                output="screen",
                parameters=[_share("mission_fsm", "config", "mission_fsm.yaml")],
            ),
            Node(
                package="fdir",
                executable="fdir_node",
                name="fdir_node",
                output="screen",
                parameters=[_share("fdir", "config", "fdir.yaml")],
            ),
            Node(
                package="gpp",
                executable="gpp_node",
                name="gpp_node",
                output="screen",
                parameters=[_share("gpp", "config", "gpp.yaml")],
            ),
            Node(
                package="daidalus_node",
                executable="daidalus_node",
                name="daidalus_node",
                output="screen",
                parameters=[_share("daidalus_node", "config", "daidalus.yaml")],
            ),
            Node(
                package="polycarp_node",
                executable="polycarp_node",
                name="polycarp_node",
                output="screen",
            ),
            Node(
                package="local_replanner",
                executable="local_replanner_node",
                name="local_replanner_node",
                output="screen",
                parameters=[_share("local_replanner", "config", "local_replanner.yaml")],
            ),
            Node(
                package="trajectory_gen",
                executable="trajectory_gen_node",
                name="trajectory_gen_node",
                output="screen",
            ),
            Node(
                package="acas_node",
                executable="acas_node",
                name="acas_node",
                output="screen",
                parameters=[_share("acas_node", "config", "acas.yaml")],
            ),
        ]
    )
