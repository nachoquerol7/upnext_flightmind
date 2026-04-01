"""
Demo grabable: TrafficMonitor DAA + marcadores RViz (ownship / intruso / texto DAA).

Todo el stack fake va bajo el namespace ROS 2 `upnext_daa` para que varios lanzamientos
no publiquen en los mismos topics /fmu/out/... (evita datos mezclados).

- use_gazebo:=false: fake PX4 (topics en /upnext_daa/fmu/out/...).
- use_gazebo:=true: PX4 real en /fmu/out/...; remapeo desde el namespace al global.
  Arranca MicroXRCEAgent (UDP 8888) para que uXRCE-DDS llegue a ROS 2.

Grabar vídeo: OBS / SimpleScreenRecorder. Datos: scripts/record_daa_smoke_demo.sh
"""

import os
import shutil
import sys

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EqualsSubstitution, LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue

DEMO_NS = 'upnext_daa'


def _micro_xrce_agent(context, *_args, **_kwargs):
    """PX4 uXRCE-DDS publica en DDS; sin agente UDP:8888 ROS 2 no ve /fmu/out/*."""
    if LaunchConfiguration('use_gazebo').perform(context) != 'true':
        return []
    if LaunchConfiguration('micro_xrce_enable').perform(context) != 'true':
        return []
    agent = LaunchConfiguration('micro_xrce_agent').perform(context).strip()
    if not agent:
        agent = os.environ.get('MICRO_XRCE_AGENT', '/usr/local/bin/MicroXRCEAgent')
    if not os.path.isfile(agent):
        w = shutil.which('MicroXRCEAgent')
        agent = w if w else ''
    if not agent or not os.path.isfile(agent):
        print(
            '[upnext_daa] AVISO: MicroXRCEAgent no encontrado — sin él PX4 no publica '
            '/fmu/out/* en ROS 2. Instala el agente o export MICRO_XRCE_AGENT.',
            file=sys.stderr,
        )
        return []
    return [
        ExecuteProcess(
            cmd=[agent, 'udp4', '-p', '8888'],
            output='screen',
            shell=False,
        )
    ]


def _auto_takeoff_actions(context, *_args, **_kwargs):
    if LaunchConfiguration('auto_takeoff').perform(context) != 'true':
        return []
    if LaunchConfiguration('use_gazebo').perform(context) != 'true':
        return []
    delay = float(LaunchConfiguration('takeoff_delay_sec').perform(context))
    alt = LaunchConfiguration('takeoff_alt').perform(context)
    conn = LaunchConfiguration('takeoff_mavlink_connection').perform(context)
    arm_only = LaunchConfiguration('auto_arm_only').perform(context) == 'true'
    exe = os.path.join(
        get_package_prefix('upnext_icarous_daa'),
        'lib',
        'upnext_icarous_daa',
        'px4_sitl_takeoff',
    )
    return [
        TimerAction(
            period=delay,
            actions=[
                ExecuteProcess(
                    cmd=(
                        [exe, '--connection', conn, '--alt', alt, '--arm-only']
                        if arm_only
                        else [exe, '--connection', conn, '--alt', alt]
                    ),
                    output='screen',
                )
            ],
        )
    ]


def _auto_set_offboard_actions(context, *_args, **_kwargs):
    if LaunchConfiguration('auto_set_offboard').perform(context) != 'true':
        return []
    if LaunchConfiguration('use_gazebo').perform(context) != 'true':
        return []
    delay = float(LaunchConfiguration('offboard_delay_sec').perform(context))
    conn = LaunchConfiguration('offboard_mavlink_connection').perform(context)
    exe = os.path.join(
        get_package_prefix('upnext_icarous_daa'),
        'lib',
        'upnext_icarous_daa',
        'px4_sitl_set_offboard',
    )
    return [
        TimerAction(
            period=delay,
            actions=[
                ExecuteProcess(
                    cmd=[exe, '--connection', conn],
                    output='screen',
                )
            ],
        )
    ]


def _daa_demo_stack(context, *args, **kwargs):
    pkg = get_package_share_directory('upnext_icarous_daa')
    cfg = os.path.join(pkg, 'config', 'upnext_daa_default.txt')
    use_gz = LaunchConfiguration('use_gazebo').perform(context) == 'true'
    remaps = []
    if use_gz:
        remaps = [
            ('fmu/out/vehicle_global_position', '/fmu/out/vehicle_global_position'),
            # PX4 reciente publica local en *_v1 (uXRCE-DDS)
            ('fmu/out/vehicle_local_position_v1', '/fmu/out/vehicle_local_position_v1'),
        ]

    bands = f'/{DEMO_NS}/daa_traffic_monitor/daa/bands_summary'
    viz_markers = f'/{DEMO_NS}/daa_demo/viz_markers'

    monitor_params = [
        {'daa_config_file': cfg},
        {'intruder_enable': True},
        {
            'intruder_n_m': ParameterValue(
                LaunchConfiguration('intruder_n_m'), value_type=float
            )
        },
        {
            'intruder_e_m': ParameterValue(
                LaunchConfiguration('intruder_e_m'), value_type=float
            )
        },
        {
            'intruder_vn': ParameterValue(
                LaunchConfiguration('intruder_vn'), value_type=float
            )
        },
        {
            'intruder_ve': ParameterValue(
                LaunchConfiguration('intruder_ve'), value_type=float
            )
        },
        {
            'intruder_vd': ParameterValue(
                LaunchConfiguration('intruder_vd'), value_type=float
            )
        },
        {
            'offboard_enable': ParameterValue(
                LaunchConfiguration('offboard_enable'), value_type=bool
            )
        },
        {
            'resolution_climb_m': ParameterValue(
                LaunchConfiguration('resolution_climb_m'), value_type=float
            )
        },
    ]

    viz_params = [
        {'bands_topic': bands},
        {'viz_topic': viz_markers},
        {'topic_global': 'fmu/out/vehicle_global_position'},
        {'topic_local': 'fmu/out/vehicle_local_position_v1'},
        {
            'intruder_n_m': ParameterValue(
                LaunchConfiguration('intruder_n_m'), value_type=float
            )
        },
        {
            'intruder_e_m': ParameterValue(
                LaunchConfiguration('intruder_e_m'), value_type=float
            )
        },
        {'title_line1': LaunchConfiguration('viz_title_line1')},
        {'title_line2': LaunchConfiguration('viz_title_line2')},
        {'geofence_enable': True},
        {
            'logo_mesh_enable': ParameterValue(
                LaunchConfiguration('viz_logo_mesh'), value_type=bool
            )
        },
    ]

    return [
        GroupAction(
            [
                PushRosNamespace(DEMO_NS),
                Node(
                    package='upnext_icarous_daa',
                    executable='fake_px4_for_daa_test',
                    name='fake_px4',
                    output='screen',
                    condition=UnlessCondition(
                        EqualsSubstitution(LaunchConfiguration('use_gazebo'), 'true')
                    ),
                ),
                Node(
                    package='upnext_icarous_daa',
                    executable='daa_traffic_monitor_node',
                    name='daa_traffic_monitor',
                    output='screen',
                    remappings=remaps,
                    parameters=monitor_params,
                ),
                Node(
                    package='upnext_icarous_daa',
                    executable='daa_demo_viz',
                    name='daa_demo_viz',
                    output='screen',
                    remappings=remaps,
                    parameters=viz_params,
                ),
            ]
        )
    ]


def generate_launch_description():
    pkg = get_package_share_directory('upnext_icarous_daa')
    bringup_share = get_package_share_directory('upnext_bringup')
    px4_launch = os.path.join(bringup_share, 'launch', 'px4_sitl.launch.py')
    rviz_cfg = os.path.join(pkg, 'config', 'daa_smoke_demo.rviz')

    return LaunchDescription(
        [
            DeclareLaunchArgument('use_rviz', default_value='true'),
            DeclareLaunchArgument(
                'use_gazebo',
                default_value='false',
                description='Arranca PX4 SITL + Gazebo (ventana del dron). Requiere PX4-Autopilot.',
            ),
            DeclareLaunchArgument(
                'px4_dir',
                default_value=os.path.expanduser('~/PX4-Autopilot'),
            ),
            DeclareLaunchArgument('vehicle', default_value='gz_x500'),
            DeclareLaunchArgument(
                'px4_gz_world',
                default_value='daa_vfr_landmarks',
                description='Mundo Gazebo (copiado a PX4 desde upnext_bringup/worlds si existe).',
            ),
            DeclareLaunchArgument(
                'px4_gz_model_pose',
                default_value='0,0,0.5,0,0,0',
                description=(
                    'Spawn PX4 ENU (m). Con auto_takeoff y delay largo, suelo en plano; '
                    'spawn en el aire sin ARM rápido = caída libre.'
                ),
            ),
            DeclareLaunchArgument(
                'auto_takeoff',
                default_value='false',
                description='Tras takeoff_delay_s, ejecuta ARM+NAV_TAKEOFF por MAVLink (solo con use_gazebo).',
            ),
            DeclareLaunchArgument('takeoff_delay_sec', default_value='50'),
            DeclareLaunchArgument('takeoff_alt', default_value='20'),
            DeclareLaunchArgument(
                'auto_arm_only',
                default_value='false',
                description='true: solo ARM (sin NAV_TAKEOFF), útil para spawn en crucero.',
            ),
            DeclareLaunchArgument(
                'takeoff_mavlink_connection',
                default_value='udp:127.0.0.1:14550',
            ),
            DeclareLaunchArgument(
                'offboard_enable',
                default_value='false',
                description=(
                    'Si true, en conflicto DAA manda TrajectorySetpoint (sube). '
                    'Requiere PX4 en modo OFFBOARD (p. ej. QGC); solo SITL/pruebas.'
                ),
            ),
            DeclareLaunchArgument(
                'resolution_climb_m',
                default_value='2.0',
                description='Magnitud de evasión vertical DAA en metros (más bajo = maniobra más suave).',
            ),
            DeclareLaunchArgument(
                'intruder_n_m',
                default_value='80.0',
                description='Intruso sintético: offset N respecto al ownship (m, NED).',
            ),
            DeclareLaunchArgument(
                'intruder_e_m',
                default_value='0.0',
                description='Intruso sintético: offset E (m, NED).',
            ),
            DeclareLaunchArgument(
                'intruder_vn',
                default_value='0.0',
                description='Velocidad intruso NED vn (m/s).',
            ),
            DeclareLaunchArgument(
                'intruder_ve',
                default_value='0.0',
                description=(
                    'Velocidad intruso ve (m/s). Prueba p.ej. -8 para cruce y bandas más dinámicas.'
                ),
            ),
            DeclareLaunchArgument(
                'intruder_vd',
                default_value='0.0',
                description='Velocidad intruso vd (m/s).',
            ),
            DeclareLaunchArgument(
                'viz_title_line1',
                default_value='UpNext UAS · Encuentro dual + DAIDALUS',
            ),
            DeclareLaunchArgument(
                'viz_title_line2',
                default_value='Geocerca · Ruta global · Evasión si hay conflicto DAA',
            ),
            DeclareLaunchArgument(
                'viz_logo_mesh',
                default_value='true',
                description='false: desactiva mesh STL del logo (menos RAM/GPU si RViz petaba).',
            ),
            DeclareLaunchArgument(
                'headless_gz',
                default_value='false',
                description='true: Gazebo sin ventana 3D (HEADLESS=1), solo servidor físico.',
            ),
            DeclareLaunchArgument(
                'micro_xrce_enable',
                default_value='true',
                description='false: no arranca MicroXRCEAgent (solo si sabes lo que haces).',
            ),
            DeclareLaunchArgument(
                'micro_xrce_agent',
                default_value='',
                description='Ruta al ejecutable MicroXRCEAgent; vacío = MICRO_XRCE_AGENT o /usr/local/bin.',
            ),
            DeclareLaunchArgument(
                'auto_set_offboard',
                default_value='false',
                description='true: envía MAV_CMD_DO_SET_MODE a OFFBOARD tras offboard_delay_sec.',
            ),
            DeclareLaunchArgument(
                'offboard_delay_sec',
                default_value='8',
                description='Delay en segundos antes de intentar OFFBOARD automático.',
            ),
            DeclareLaunchArgument(
                'offboard_mavlink_connection',
                default_value='udp:127.0.0.1:14550',
                description='Endpoint MAVLink para cambiar a OFFBOARD automáticamente.',
            ),
            OpaqueFunction(function=_micro_xrce_agent),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(px4_launch),
                launch_arguments=[
                    ('px4_dir', LaunchConfiguration('px4_dir')),
                    ('vehicle', LaunchConfiguration('vehicle')),
                    ('px4_gz_world', LaunchConfiguration('px4_gz_world')),
                    ('px4_gz_model_pose', LaunchConfiguration('px4_gz_model_pose')),
                    ('headless_gz', LaunchConfiguration('headless_gz')),
                ],
                condition=IfCondition(
                    EqualsSubstitution(LaunchConfiguration('use_gazebo'), 'true')
                ),
            ),
            OpaqueFunction(function=_daa_demo_stack),
            # Retraso: Gazebo+PX4+EKF; sube si RViz abre en vacío o sin marcadores.
            TimerAction(
                period=4.0,
                actions=[
                    Node(
                        package='rviz2',
                        executable='rviz2',
                        name='rviz',
                        arguments=['-d', rviz_cfg],
                        condition=IfCondition(
                            EqualsSubstitution(LaunchConfiguration('use_rviz'), 'true')
                        ),
                    ),
                ],
            ),
            OpaqueFunction(function=_auto_takeoff_actions),
            OpaqueFunction(function=_auto_set_offboard_actions),
        ]
    )
