import os
from glob import glob

from setuptools import setup

package_name = 'vehicle_model'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ignacio',
    maintainer_email='ignacio@example.com',
    description='Fixed-wing vehicle envelope model and latched ROS 2 state publisher.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vehicle_model_node = vehicle_model.vehicle_model_node:main',
        ],
    },
)
