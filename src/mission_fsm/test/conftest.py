"""Fixtures SIL compartidos (Fase 0 roadmap V&V)."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Generator

import pytest
import yaml
from flightmind_msgs.msg import FSMState
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

import rclpy

_TEST_DIR = Path(__file__).resolve().parent
_MOCKS = _TEST_DIR / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import fsm_input_injector  # noqa: E402

from mission_fsm.fsm import default_inputs
from mission_fsm.mission_fsm_node import MissionFsmNode


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "no_ros: test estático sin grafo ROS 2")
    config.addinivalue_line("markers", "slow: tests que arrancan nodos ROS2 reales")
    config.addinivalue_line("markers", "tight_dwell: FSM conserva max_duration_sec del YAML (solo M2 morada)")
    config.addinivalue_line("markers", "demo: tests incluidos en la suite de demo para el 8 de abril")
    # Colcon sometimes picks a rootdir without package pytest.ini; enforce a ceiling on hangs.
    if config.pluginmanager.has_plugin("timeout"):
        to = getattr(config.option, "timeout", None)
        # pytest-timeout: None if unset; 0 disables — only apply a default when unset.
        if to is None:
            config.option.timeout = 30


class _FsmModeCapture(Node):
    """Último modo y trigger publicados por mission_fsm_node."""

    def __init__(self) -> None:
        super().__init__("fsm_mode_capture")
        self.mode = ""
        self.trig = ""
        self.triggers: list[str] = []
        # Volatile + cola amplia: evita histórico de otra ejecución; depth 50 reduce pérdidas a 20 Hz.
        cap_qos = QoSProfile(
            depth=100,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(FSMState, "/fsm/state", self._on_state, cap_qos)

    def _on_state(self, msg: FSMState) -> None:
        self.mode = msg.current_mode
        self.trig = msg.active_trigger
        if msg.active_trigger:
            self.triggers.append(msg.active_trigger)


def spin_until(ex: MultiThreadedExecutor, pred: Callable[[], bool], *, timeout_sec: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        for _ in range(24):
            ex.spin_once(timeout_sec=0.02)
        if pred():
            return True
    return False


@pytest.fixture
def ros_context() -> Generator[None, None, None]:
    """Inicializa y destruye rclpy por test."""
    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()
    yield
    rclpy.shutdown()


@pytest.fixture
def yaml_config() -> Dict[str, Any]:
    """Carga config/mission_fsm.yaml como dict."""
    root = Path(__file__).resolve().parents[1]
    path = root / "config" / "mission_fsm.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    return data


@pytest.fixture
def fsm_params(yaml_config: Dict[str, Any]) -> Dict[str, Any]:
    """Parámetros ROS declarados en YAML bajo mission_fsm_node.ros__parameters."""
    node = yaml_config.get("mission_fsm_node") or {}
    params = node.get("ros__parameters") or {}
    if not isinstance(params, dict):
        return {}
    out: Dict[str, Any] = dict(params)
    # max_duration_sec: buscar bajo fsm.states.* si existen (extensión futura)
    fsm = yaml_config.get("fsm") or {}
    states = (fsm.get("states") or {}) if isinstance(fsm, dict) else {}
    max_durations: Dict[str, Any] = {}
    if isinstance(states, dict):
        for name, body in states.items():
            if isinstance(body, dict) and "max_duration_sec" in body:
                max_durations[str(name)] = body["max_duration_sec"]
    if max_durations:
        out["_max_duration_sec_by_state"] = max_durations
    return out


@pytest.fixture
def mission_fsm_sil_harness(ros_context: None, request: pytest.FixtureRequest) -> Generator[SimpleNamespace, None, None]:
    """mission_fsm_node + FsmInputInjector + captura de /fsm/current_mode y /fsm/active_trigger."""
    ex = MultiThreadedExecutor()
    fsm = MissionFsmNode()
    inj = fsm_input_injector.create_fsm_input_injector()
    cap = _FsmModeCapture()
    ex.add_node(fsm)
    ex.add_node(inj)
    ex.add_node(cap)
    if not request.node.get_closest_marker("tight_dwell"):
        for k in fsm._fsm._max_duration_by_state:  # noqa: SLF001
            fsm._fsm._max_duration_by_state[k] = 3600.0  # noqa: SLF001
    # Reset deterministic start to avoid transient-local latched samples from previous tests.
    fsm._fsm.reset("PREFLIGHT")  # noqa: SLF001
    fsm._inputs = default_inputs()  # noqa: SLF001
    spin_until(ex, lambda: fsm._fsm.state == "PREFLIGHT", timeout_sec=3.0)
    cap.mode = fsm._fsm.state
    cap.trig = ""
    cap.triggers.clear()

    def wait_mode(expected: str, *, timeout_sec: float = 3.0) -> bool:
        def _match() -> bool:
            m = cap.mode
            return m == expected or m.startswith(f"{expected}:")

        return spin_until(ex, _match, timeout_sec=timeout_sec)

    def wait_trig(expected: str, *, timeout_sec: float = 3.0) -> bool:
        return spin_until(ex, lambda: cap.trig == expected, timeout_sec=timeout_sec)

    h = SimpleNamespace(
        ex=ex,
        fsm=fsm,
        inj=inj,
        cap=cap,
        spin_until=lambda pred, timeout_sec=3.0: spin_until(ex, pred, timeout_sec=timeout_sec),
        wait_mode=wait_mode,
        wait_trig=wait_trig,
    )
    yield h
    ex.remove_node(fsm)
    ex.remove_node(inj)
    ex.remove_node(cap)
    fsm.destroy_node()
    inj.destroy_node()
    cap.destroy_node()
