import os
from glob import glob

from setuptools import setup

package_name = "uas_stack_tests"
_launch = glob("launch/*") if os.path.isdir("launch") else []
_docs = glob("docs/*") if os.path.isdir("docs") else []
_scripts = glob("scripts/*.py") if os.path.isdir("scripts") else []

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name, f"{package_name}.scenarios"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        *([(os.path.join("share", package_name, "launch"), _launch)] if _launch else []),
        *([(os.path.join("share", package_name, "docs"), _docs)] if _docs else []),
        *([(os.path.join("share", package_name, "scripts"), _scripts)] if _scripts else []),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ignacio",
    maintainer_email="ignacio@example.com",
    description="End-to-end stack launch, SIL scenarios, V&V matrix (Phase 9).",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "fake_fmu_shim = uas_stack_tests.fake_fmu_shim:main",
            "stack_integration_feeds = uas_stack_tests.stack_integration_feeds:main",
            "scenario_head_on = uas_stack_tests.scenarios.head_on:main",
            "scenario_overtake = uas_stack_tests.scenarios.overtake:main",
            "scenario_crossing = uas_stack_tests.scenarios.crossing:main",
            "scenario_geofence = uas_stack_tests.scenarios.geofence:main",
            "daa_dashboard = uas_stack_tests.dashboard:main",
        ],
    },
)
