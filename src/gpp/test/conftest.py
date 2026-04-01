from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Callable

import pytest
import rclpy
from nav_msgs.msg import Path
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import Float64, Float64MultiArray, String

from gpp.gpp_node import GppNode


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "ros: test que usa rclpy y nodos ROS2")


@pytest.fixture(scope="session")
def ros_context() -> None:
    rclpy.init()
    yield
    rclpy.shutdown()


@pytest.fixture
def gpp_runtime(ros_context: None) -> SimpleNamespace:
    node = GppNode()
    spy = rclpy.create_node("gpp_test_spy")
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    ex.add_node(spy)

    cap = SimpleNamespace(status=None, fl=None, path=None, takeoff_phase=None)

    spy.create_subscription(String, "/gpp/status", lambda m: setattr(cap, "status", m.data), 10)
    spy.create_subscription(Float64, "/gpp/assigned_fl", lambda m: setattr(cap, "fl", m.data), 10)
    spy.create_subscription(Path, "/gpp/global_path", lambda m: setattr(cap, "path", m), 10)
    spy.create_subscription(String, "/gpp/takeoff_phase", lambda m: setattr(cap, "takeoff_phase", m.data), 10)

    pubs = SimpleNamespace(
        terrain=spy.create_publisher(Float64, "/gpp/terrain_max_m", 10),
        ceiling=spy.create_publisher(Float64, "/gpp/ceiling_m", 10),
        quality=spy.create_publisher(Float64, "/nav/quality_flag", 10),
        goal=spy.create_publisher(Float64MultiArray, "/gpp/goal", 10),
        geo=spy.create_publisher(String, "/airspace/geofences", 10),
        ownship=spy.create_publisher(Float64MultiArray, "/ownship/state", 10),
        takeoff=spy.create_publisher(Float64MultiArray, "/gpp/takeoff_state", 10),
    )

    def spin_for(seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            ex.spin_once(timeout_sec=0.02)

    def wait_until(pred: Callable[[], bool], timeout_sec: float = 2.0) -> bool:
        end = time.time() + timeout_sec
        while time.time() < end:
            ex.spin_once(timeout_sec=0.02)
            if pred():
                return True
        return False

    rt = SimpleNamespace(node=node, spy=spy, ex=ex, cap=cap, pubs=pubs, spin_for=spin_for, wait_until=wait_until)
    yield rt
    ex.remove_node(spy)
    ex.remove_node(node)
    spy.destroy_node()
    node.destroy_node()
