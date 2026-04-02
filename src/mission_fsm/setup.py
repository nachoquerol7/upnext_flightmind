import os
from glob import glob

from setuptools import setup

package_name = "mission_fsm"
_docs_vnv = glob("docs/vnv/*") if os.path.isdir("docs/vnv") else []
_launch = glob("launch/*.py") if os.path.isdir("launch") else []

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        *([(os.path.join("share", package_name, "launch"), _launch)] if _launch else []),
        *(
            [(os.path.join("share", package_name, "docs", "vnv"), _docs_vnv)]
            if _docs_vnv
            else []
        ),
    ],
    install_requires=["setuptools", "flightmind_msgs"],
    zip_safe=True,
    maintainer="ignacio",
    maintainer_email="ignacio@example.com",
    description="Mission FSM with YAML guards/transitions and ROS 2 mode/trigger topics.",
    license="Apache-2.0",
    tests_require=["pytest", "pytest-timeout"],
    entry_points={
        "console_scripts": [
            "mission_fsm_node = mission_fsm.mission_fsm_node:main",
            "navigation_quality_relay_node = mission_fsm.navigation_quality_relay_node:main",
        ],
    },
)
