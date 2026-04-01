"""DAA + Gazebo + RViz en crucero: spawn en altura + auto-arm sin takeoff."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = get_package_share_directory('upnext_icarous_daa')
    demo = os.path.join(pkg, 'launch', 'daa_smoke_demo.launch.py')
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'takeoff_delay_sec',
                default_value='3',
                description='Segundos hasta ARM automático en crucero.',
            ),
            DeclareLaunchArgument('takeoff_alt', default_value='20'),
            DeclareLaunchArgument(
                'vehicle',
                default_value='gz_x500',
                description='Modelo PX4 Gazebo. gz_x500 por defecto (auto-takeoff más robusto).',
            ),
            DeclareLaunchArgument(
                'px4_dir',
                default_value=os.path.expanduser('~/PX4-Autopilot'),
            ),
            DeclareLaunchArgument(
                'px4_gz_world',
                default_value='daa_dem_srtm',
                description='Mundo con relieve (DEM) para ver terreno en simulación.',
            ),
            DeclareLaunchArgument(
                'px4_gz_model_pose',
                default_value='0,0,320,0,0,0',
                description='Spawn ENU en crucero medio (visualiza mejor el terreno).',
            ),
            DeclareLaunchArgument(
                'auto_takeoff',
                default_value='false',
                description='Modo crucero directo: sin script ARM/TAKEOFF automático.',
            ),
            DeclareLaunchArgument(
                'auto_arm_only',
                default_value='false',
                description='Solo aplica si auto_takeoff=true.',
            ),
            DeclareLaunchArgument(
                'auto_set_offboard',
                default_value='true',
                description='Intenta poner PX4 en OFFBOARD automáticamente (demo DAA evasión).',
            ),
            DeclareLaunchArgument(
                'offboard_delay_sec',
                default_value='10',
                description='Espera antes de solicitar OFFBOARD por MAVLink.',
            ),
            DeclareLaunchArgument(
                'headless_gz',
                default_value='false',
                description='true: sin ventana Gazebo (menos GPU). Ver scripts/gui_daa_flying_demo_lite.sh',
            ),
            DeclareLaunchArgument(
                'micro_xrce_enable',
                default_value='true',
                description='Arranca MicroXRCEAgent para bridgar PX4 → ROS 2 (/fmu/out/*).',
            ),
            DeclareLaunchArgument('micro_xrce_agent', default_value=''),
            DeclareLaunchArgument(
                'viz_logo_mesh',
                default_value='true',
                description='false: menos RAM (recomendado en modo lite).',
            ),
            DeclareLaunchArgument('use_rviz', default_value='true'),
            DeclareLaunchArgument(
                'offboard_enable',
                default_value='true',
                description='DAA manda subida por offboard en conflicto.',
            ),
            DeclareLaunchArgument(
                'resolution_climb_m',
                default_value='2.0',
                description='Evasión vertical DAA (m), suavizada para demo visual.',
            ),
            DeclareLaunchArgument('intruder_n_m', default_value='80.0'),
            DeclareLaunchArgument('intruder_e_m', default_value='0.0'),
            DeclareLaunchArgument('intruder_vn', default_value='0.0'),
            DeclareLaunchArgument('intruder_ve', default_value='0.0'),
            DeclareLaunchArgument('intruder_vd', default_value='0.0'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(demo),
                launch_arguments=[
                    ('use_gazebo', 'true'),
                    ('use_rviz', LaunchConfiguration('use_rviz')),
                    ('auto_takeoff', LaunchConfiguration('auto_takeoff')),
                    ('auto_arm_only', LaunchConfiguration('auto_arm_only')),
                    ('auto_set_offboard', LaunchConfiguration('auto_set_offboard')),
                    ('offboard_delay_sec', LaunchConfiguration('offboard_delay_sec')),
                    ('takeoff_delay_sec', LaunchConfiguration('takeoff_delay_sec')),
                    ('takeoff_alt', LaunchConfiguration('takeoff_alt')),
                    ('vehicle', LaunchConfiguration('vehicle')),
                    ('px4_dir', LaunchConfiguration('px4_dir')),
                    ('px4_gz_world', LaunchConfiguration('px4_gz_world')),
                    ('px4_gz_model_pose', LaunchConfiguration('px4_gz_model_pose')),
                    ('headless_gz', LaunchConfiguration('headless_gz')),
                    ('micro_xrce_enable', LaunchConfiguration('micro_xrce_enable')),
                    ('micro_xrce_agent', LaunchConfiguration('micro_xrce_agent')),
                    ('viz_logo_mesh', LaunchConfiguration('viz_logo_mesh')),
                    ('offboard_enable', LaunchConfiguration('offboard_enable')),
                    ('resolution_climb_m', LaunchConfiguration('resolution_climb_m')),
                    ('intruder_n_m', LaunchConfiguration('intruder_n_m')),
                    ('intruder_e_m', LaunchConfiguration('intruder_e_m')),
                    ('intruder_vn', LaunchConfiguration('intruder_vn')),
                    ('intruder_ve', LaunchConfiguration('intruder_ve')),
                    ('intruder_vd', LaunchConfiguration('intruder_vd')),
                ],
            ),
        ]
    )
