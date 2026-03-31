from glob import glob
import os
from setuptools import find_packages, setup

package_name = 'upnext_airspace'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ignacio-querol',
    maintainer_email='ignacio-querol@todo.todo',
    description='Airspace GeoJSON + RViz + PX4 monitor.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'airspace_viz_node = upnext_airspace.airspace_viz_node:main',
            'airspace_monitor_node = upnext_airspace.airspace_monitor_node:main',
        ],
    },
)
