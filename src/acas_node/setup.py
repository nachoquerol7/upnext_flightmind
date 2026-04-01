import os
from glob import glob

from setuptools import setup

package_name = "acas_node"
_cfg = glob("config/*") if os.path.isdir("config") else []
_launch = glob("launch/*") if os.path.isdir("launch") else []

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        *([(os.path.join("share", package_name, "config"), _cfg)] if _cfg else []),
        *([(os.path.join("share", package_name, "launch"), _launch)] if _launch else []),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ignacio",
    maintainer_email="ignacio@example.com",
    description="ACAS Xu-style RT advisory node (Fase 8).",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "acas_node = acas_node.acas_node:main",
        ],
    },
)
