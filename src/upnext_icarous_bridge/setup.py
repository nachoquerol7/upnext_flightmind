from glob import glob
import os
from setuptools import find_packages, setup

package_name = 'upnext_icarous_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ignacio-querol',
    maintainer_email='ignacio-querol@todo.todo',
    description='ICAROUS workspace bridge for UpNext.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'icarous_bridge_node = upnext_icarous_bridge.bridge_node:main',
        ],
    },
)
