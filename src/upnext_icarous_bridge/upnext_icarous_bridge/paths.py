"""Resolve ICAROUS checkout inside the colcon workspace."""

import os

from ament_index_python.packages import get_package_prefix


def workspace_root_from_install_prefix(package_name: str) -> str:
    """install/<pkg> -> workspace root (parent of install/)."""
    prefix = get_package_prefix(package_name)
    return os.path.abspath(os.path.join(prefix, '..', '..'))


def default_icarous_home() -> str:
    root = workspace_root_from_install_prefix('upnext_icarous_bridge')
    return os.path.join(root, 'third_party', 'icarous')
