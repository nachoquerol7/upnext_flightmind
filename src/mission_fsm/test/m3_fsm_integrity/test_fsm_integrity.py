"""M3 — Integridad estática del grafo FSM (TC-INT-001 … TC-INT-008)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Set

import pytest
import rclpy
import yaml
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String

from mission_fsm.fsm import BUILTINS, default_inputs, load_fsm_yaml_dict
from mission_fsm.mission_fsm_node import MissionFsmNode


def _yaml_path() -> str:
    import os

    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "mission_fsm.yaml")
    )


def _collect_atoms(cond: Any) -> Set[str]:
    if cond is None or cond == {}:
        return set()
    if isinstance(cond, str):
        return {cond}
    if isinstance(cond, dict):
        out: Set[str] = set()
        if "all" in cond:
            for x in cond["all"]:
                out |= _collect_atoms(x)
        if "any" in cond:
            for x in cond["any"]:
                out |= _collect_atoms(x)
        if "not" in cond:
            out |= _collect_atoms(cond["not"])
        return out
    return set()


@pytest.mark.no_ros
def test_tc_int001_yaml_loads_as_mapping() -> None:
    """TC-INT-001: el YAML raíz es un mapping con sección fsm."""
    with open(_yaml_path(), encoding="utf-8") as f:
        root = yaml.safe_load(f)
    assert isinstance(root, dict) and isinstance(root.get("fsm"), dict)


@pytest.mark.no_ros
def test_tc_int002_transition_endpoints_are_declared_states() -> None:
    """TC-INT-002: cada transición referencia estados definidos en fsm.states."""
    root = load_fsm_yaml_dict(_yaml_path())
    fsm = root["fsm"]
    states = set(fsm["states"].keys())
    for t in fsm["transitions"]:
        assert str(t["from"]) in states
        assert str(t["to"]) in states


@pytest.mark.no_ros
def test_tc_int003_initial_state_exists_in_fsm_states() -> None:
    """TC-INT-003: initial_state del YAML está en fsm.states."""
    root = load_fsm_yaml_dict(_yaml_path())
    initial = str(root["mission_fsm_node"]["ros__parameters"]["initial_state"])
    assert initial in root["fsm"]["states"]


@pytest.mark.no_ros
def test_tc_int004_transition_condition_atoms_are_known() -> None:
    """TC-INT-004: átomos en `when` son builtins o entradas por defecto del FSM."""
    allowed = set(BUILTINS.keys()) | set(default_inputs().keys())
    root = load_fsm_yaml_dict(_yaml_path())
    for t in root["fsm"]["transitions"]:
        atoms = _collect_atoms(t.get("when", {}))
        for a in atoms:
            assert a in allowed, f"unknown atom in transition when: {a!r}"


@pytest.mark.no_ros
def test_tc_int005_entry_guard_atoms_are_known() -> None:
    """TC-INT-005: átomos en entry_guards de estados son conocidos."""
    allowed = set(BUILTINS.keys()) | set(default_inputs().keys())
    root = load_fsm_yaml_dict(_yaml_path())
    for _name, spec in root["fsm"]["states"].items():
        atoms = _collect_atoms(spec.get("entry_guards", {}))
        for a in atoms:
            assert a in allowed, f"unknown atom in entry_guards: {a!r}"


@pytest.mark.no_ros
def test_tc_int006_each_state_reachable_or_is_initial() -> None:
    """TC-INT-006: todo estado aparece como `to` o es el initial (grafo referenciado)."""
    root = load_fsm_yaml_dict(_yaml_path())
    states: Set[str] = set(root["fsm"]["states"].keys())
    initial = str(root["mission_fsm_node"]["ros__parameters"]["initial_state"])
    targets: Set[str] = {initial}
    for t in root["fsm"]["transitions"]:
        targets.add(str(t["to"]))
    assert states == targets


@pytest.mark.skip(reason="Ejecutar tras M1+M2 completos (cobertura transiciones)")
@pytest.mark.no_ros
def test_tc_int007_transition_coverage_placeholder() -> None:
    assert False


def test_tc_int008_mission_fsm_node_publishes_mode_within_startup_window() -> None:
    """TC-INT-008: el nodo publica /fsm/current_mode tras arranque en ventana breve."""
    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()
    received: List[str] = []

    class _Sub(Node):
        def __init__(self) -> None:
            super().__init__("tc_int008_listener")
            self.create_subscription(String, "/fsm/current_mode", self._cb, 10)

        def _cb(self, msg: String) -> None:
            received.append(msg.data)

    t0 = time.monotonic()
    fsm = MissionFsmNode()
    sub = _Sub()
    ex = MultiThreadedExecutor()
    ex.add_node(fsm)
    ex.add_node(sub)
    for _ in range(50):
        ex.spin_once(timeout_sec=0.05)
        if received:
            break
    dt = time.monotonic() - t0
    fsm.destroy_node()
    sub.destroy_node()
    rclpy.shutdown()
    assert dt < 5.0 and len(received) >= 1
