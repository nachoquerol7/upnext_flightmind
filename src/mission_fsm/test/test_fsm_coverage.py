"""Cobertura de ramas en mission_fsm.fsm (eval_condition, YAML, step, reset, load)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pytest

from mission_fsm.fsm import (
    MissionFsm,
    default_inputs,
    eval_condition,
    load_fsm_yaml_dict,
    mission_fsm_from_path,
)


def test_eval_condition_non_bool_input_atom_uses_bool_conversion() -> None:
    """Rama str en inputs: no bool → bool(v) (línea 47)."""
    inputs: Dict[str, Any] = dict(default_inputs())
    inputs["custom_atom"] = 1
    assert eval_condition("custom_atom", inputs, {"quality_flag_threshold": 0.5, "daidalus_alert_amber": 1}) is True


def test_eval_condition_unknown_atom_raises() -> None:
    with pytest.raises(KeyError, match="unknown condition atom"):
        eval_condition("not_in_inputs", default_inputs(), {"quality_flag_threshold": 0.5, "daidalus_alert_amber": 1})


def test_eval_condition_invalid_type_raises() -> None:
    with pytest.raises(TypeError, match="invalid condition type"):
        eval_condition(42, default_inputs(), {"quality_flag_threshold": 0.5, "daidalus_alert_amber": 1})


def test_eval_condition_not_branch() -> None:
    ctx = {"quality_flag_threshold": 0.5, "daidalus_alert_amber": 1}
    inputs = dict(default_inputs())
    assert (
        eval_condition({"not": {"all": ["preflight_ok"]}}, inputs, ctx) is True
    )


def test_eval_condition_unknown_mapping_keys_raises() -> None:
    with pytest.raises(KeyError, match="unknown condition keys"):
        eval_condition({"weird": True}, default_inputs(), {"quality_flag_threshold": 0.5, "daidalus_alert_amber": 1})


def test_from_fsm_yaml_fsm_missing_or_invalid() -> None:
    with pytest.raises(ValueError, match="fsm root missing"):
        MissionFsm.from_fsm_yaml({"mission_fsm_node": {"ros__parameters": {}}})
    with pytest.raises(ValueError, match="fsm root missing"):
        MissionFsm.from_fsm_yaml({"fsm": []})


def test_from_fsm_yaml_states_or_transitions_wrong_type() -> None:
    with pytest.raises(ValueError, match="fsm.states"):
        MissionFsm.from_fsm_yaml({"fsm": {"states": [], "transitions": []}})
    with pytest.raises(ValueError, match="fsm.states"):
        MissionFsm.from_fsm_yaml({"fsm": {"states": {}, "transitions": {}}})


def test_from_fsm_yaml_ros_params_not_dict_uses_empty() -> None:
    root = {
        "mission_fsm_node": {"ros__parameters": "not-a-dict"},
        "fsm": {"states": {"PREFLIGHT": {"entry_guards": {}}}, "transitions": []},
    }
    m = MissionFsm.from_fsm_yaml(root)
    assert m.state == "PREFLIGHT"


def test_from_fsm_yaml_parameter_overlay_extra_keys() -> None:
    path = os.path.join(os.path.dirname(__file__), "..", "config", "mission_fsm.yaml")
    path = os.path.abspath(path)
    m = mission_fsm_from_path(
        path,
        parameter_overlay={
            "quality_flag_threshold": 0.9,
            "daidalus_alert_amber": 2,
            "custom_ctx": 3,
        },
    )
    assert m._context.get("custom_ctx") == 3  # noqa: SLF001


def test_from_fsm_yaml_state_body_not_mapping_raises() -> None:
    root = {
        "mission_fsm_node": {"ros__parameters": {"initial_state": "PREFLIGHT"}},
        "fsm": {"states": {"PREFLIGHT": "bad"}, "transitions": []},
    }
    with pytest.raises(ValueError, match="state PREFLIGHT must be a mapping"):
        MissionFsm.from_fsm_yaml(root)


def test_step_entry_guard_blocks_transition() -> None:
    """Rama continue cuando entry_guard del destino falla (línea 167)."""
    m = MissionFsm(
        initial_state="A",
        context={
            "quality_flag_threshold": 0.5,
            "daidalus_alert_amber": 1,
            "tick_hz": 10.0,
            "hysteresis_ticks_on": 3,
            "hysteresis_ticks_off": 5,
            "hysteresis_margin": 0.05,
            "daidalus_escalate_ticks": 2,
        },
        state_entry={"B": {"all": ["must_be_false"]}},
        transitions=[{"from": "A", "to": "B", "trigger": "try_b", "when": {"all": ["go"]}}],
    )
    s, t = m.step({"go": True, "must_be_false": False})
    assert s == "A" and t is None


def test_reset_with_and_without_argument() -> None:
    path = os.path.join(os.path.dirname(__file__), "..", "config", "mission_fsm.yaml")
    path = os.path.abspath(path)
    m = mission_fsm_from_path(path)
    m.seed("CRUISE")
    m.reset()
    assert m.state == "PREFLIGHT"
    m.seed("CRUISE")
    m.reset("LANDING")
    assert m.state == "LANDING"


def test_load_fsm_yaml_dict_root_not_mapping_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("- not_a: mapping_root\n", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML root must be a mapping"):
        load_fsm_yaml_dict(str(p))
