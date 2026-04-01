"""Fase 0 V&V: humo de fixtures y mocks (sin TC funcionales del roadmap)."""

from __future__ import annotations

import sys
from pathlib import Path

import rclpy

# Imports de mocks por ruta (test/ no es paquete instalado)
_MOCKS = Path(__file__).resolve().parent / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_daidalus  # noqa: E402
import mock_fastlio2  # noqa: E402
import mock_fdir  # noqa: E402
import mock_nav2  # noqa: E402
import mock_px4_bridge  # noqa: E402
import mock_sensors  # noqa: E402


def test_yaml_config_contains_fsm_root(yaml_config: dict) -> None:
    assert "fsm" in yaml_config


def test_fsm_params_exposes_thresholds(fsm_params: dict) -> None:
    assert fsm_params.get("quality_flag_threshold") == 0.5


def test_mock_fastlio2_spins(ros_context: None) -> None:
    node = mock_fastlio2.create_mock_fastlio2()
    rclpy.spin_once(node, timeout_sec=0.2)
    name = node.get_name()
    node.destroy_node()
    assert name == "mock_fastlio2"


def test_mock_daidalus_spins(ros_context: None) -> None:
    node = mock_daidalus.create_mock_daidalus()
    rclpy.spin_once(node, timeout_sec=0.2)
    name = node.get_name()
    node.destroy_node()
    assert name == "mock_daidalus"


def test_mock_fdir_spins(ros_context: None) -> None:
    node = mock_fdir.create_mock_fdir()
    rclpy.spin_once(node, timeout_sec=0.2)
    name = node.get_name()
    node.destroy_node()
    assert name == "mock_fdir"


def test_mock_nav2_spins(ros_context: None) -> None:
    node = mock_nav2.create_mock_nav2()
    rclpy.spin_once(node, timeout_sec=0.2)
    name = node.get_name()
    node.destroy_node()
    assert name == "mock_nav2"


def test_mock_px4_bridge_spins(ros_context: None) -> None:
    node = mock_px4_bridge.create_mock_px4_bridge()
    rclpy.spin_once(node, timeout_sec=0.2)
    name = node.get_name()
    node.destroy_node()
    assert name == "mock_px4_bridge"


def test_mock_sensors_spins(ros_context: None) -> None:
    node = mock_sensors.create_mock_sensors()
    rclpy.spin_once(node, timeout_sec=0.2)
    name = node.get_name()
    node.destroy_node()
    assert name == "mock_sensors"


def test_mock_daidalus_inject_updates_alert(ros_context: None) -> None:
    node = mock_daidalus.create_mock_daidalus()
    node.inject("alert_level", 2)
    assert node.alert_level == 2
    node.destroy_node()
