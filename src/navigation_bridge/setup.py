import os

from setuptools import setup

package_name = "navigation_bridge"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ignacio",
    maintainer_email="ignacio@example.com",
    description="PX4 odometry to NavigationState bridge.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "navigation_bridge_node = navigation_bridge.navigation_bridge_node:main",
        ],
    },
)
