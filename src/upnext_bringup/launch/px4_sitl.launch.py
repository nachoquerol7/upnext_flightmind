"""
PX4 SITL con Gazebo (gz): por defecto mundo `daa_vfr_landmarks` (terreno plano + marcas VFR)
y spawn en suelo ~0,5 m ENU (evita caída libre antes de ARM si usas auto_takeoff con delay largo).

Spawn en el aire (z alto) sin empuje: caída al suelo en ~sqrt(2h/g) s — antes de que arme
px4_sitl_takeoff. Para VFR alto: reduce takeoff_delay_sec o despega a mano.

El init de PX4 usa PX4_GZ_WORLDS desde gz_env.sh (carpeta de mundos del propio PX4),
así que este launch copia el .sdf del paquete a Tools/simulation/gz/worlds/ antes de make.

Override: px4_gz_world:=daa_high_altitude px4_gz_model_pose:=0,0,6096,0,0,0 para crucero alto;
px4_gz_world:=default px4_gz_model_pose:=0,0,0.1,0,0,0 para el mundo gris clásico.
"""

import glob
import os
import shutil

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration


def _px4_sitl(context, *_args, **_kwargs):
    px4_dir = LaunchConfiguration('px4_dir').perform(context)
    vehicle = LaunchConfiguration('vehicle').perform(context)
    gz_world = LaunchConfiguration('px4_gz_world').perform(context)
    gz_pose = LaunchConfiguration('px4_gz_model_pose').perform(context)
    px4_dir = os.path.expanduser(px4_dir)
    if not os.path.isdir(px4_dir):
        raise FileNotFoundError(
            f'PX4-Autopilot not found at {px4_dir}. Set px4_dir or clone PX4.'
        )

    px4_worlds = os.path.join(px4_dir, 'Tools', 'simulation', 'gz', 'worlds')
    try:
        pkg_share = get_package_share_directory('upnext_bringup')
    except LookupError as e:
        raise RuntimeError(
            'Paquete upnext_bringup no instalado (source install/setup.bash tras colcon build).'
        ) from e
    worlds_dir = os.path.join(pkg_share, 'worlds')
    pkg_world = os.path.join(worlds_dir, f'{gz_world}.sdf')
    if os.path.isfile(pkg_world):
        os.makedirs(px4_worlds, exist_ok=True)
        dst = os.path.join(px4_worlds, f'{gz_world}.sdf')
        shutil.copyfile(pkg_world, dst)
        # Recursos junto al mundo (heightmaps PNG, etc.): mismo prefijo que el nombre del mundo
        for extra in glob.glob(os.path.join(worlds_dir, f'{gz_world}_*.png')):
            if os.path.isfile(extra):
                shutil.copyfile(extra, os.path.join(px4_worlds, os.path.basename(extra)))

    # Importante: NO usar env=os.environ.copy() — Launch ignora context.environment y se pierden
    # AMENT_*, ROS_* y otras variables que inyecta ros2 launch. Solo additional_env.
    additional = {
        'PX4_GZ_WORLD': gz_world,
        'PX4_GZ_MODEL_POSE': gz_pose,
    }
    if 'PX4_GZ_FOLLOW_OFFSET_X' not in context.environment:
        additional['PX4_GZ_FOLLOW_OFFSET_X'] = '-25'
    if 'PX4_GZ_FOLLOW_OFFSET_Y' not in context.environment:
        additional['PX4_GZ_FOLLOW_OFFSET_Y'] = '-25'
    if 'PX4_GZ_FOLLOW_OFFSET_Z' not in context.environment:
        additional['PX4_GZ_FOLLOW_OFFSET_Z'] = '12'

    if LaunchConfiguration('headless_gz').perform(context) == 'true':
        additional['HEADLESS'] = '1'

    return [
        ExecuteProcess(
            cmd=['make', '-C', px4_dir, 'px4_sitl', vehicle],
            output='screen',
            shell=False,
            additional_env=additional,
        )
    ]


def generate_launch_description():
    # Suelo por defecto: con auto_takeoff a los 40–50 s, spawn en el aire = caída libre al suelo.
    default_pose = '0,0,0.5,0,0,0'
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
            DeclareLaunchArgument(
                'px4_gz_world',
                default_value='daa_vfr_landmarks',
                description=(
                    'Mundo: daa_vfr_landmarks (VFR), daa_dem_srtm (SRTM+PNG), '
                    'daa_high_altitude (crucero), default (PX4).'
                ),
            ),
            DeclareLaunchArgument(
                'px4_gz_model_pose',
                default_value=default_pose,
                description='PX4_GZ_MODEL_POSE: x,y,z,roll,pitch,yaw (metros, rad).',
            ),
            DeclareLaunchArgument(
                'headless_gz',
                default_value='false',
                description='true: no abre ventana gz gui (menos GPU; sim sigue en servidor).',
            ),
            OpaqueFunction(function=_px4_sitl),
        ]
    )
