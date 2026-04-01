"""One pytest per transition defined in config/mission_fsm.yaml."""

from __future__ import annotations

import os
from typing import Any, Dict

import pytest

from mission_fsm.fsm import default_inputs, mission_fsm_from_path


def _yaml_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "mission_fsm.yaml"))


def _fsm():
    return mission_fsm_from_path(_yaml_path())


def _base(**kwargs):
    d = default_inputs()
    d.update(kwargs)
    return d


def test_transition_to_autotaxi() -> None:
    m = _fsm()
    s, t = m.step(_base(preflight_ok=True))
    assert s == "AUTOTAXI" and t == "to_autotaxi"


def test_transition_to_takeoff() -> None:
    m = _fsm()
    m.seed("AUTOTAXI")
    s, t = m.step(_base(preflight_ok=True, taxi_clear=True))
    assert s == "TAKEOFF" and t == "to_takeoff"


def test_transition_to_cruise() -> None:
    m = _fsm()
    m.seed("TAKEOFF")
    s, t = m.step(_base(taxi_clear=True, takeoff_complete=True))
    assert s == "CRUISE" and t == "to_cruise"


def test_transition_cruise_to_abort() -> None:
    m = _fsm()
    m.seed("CRUISE")
    s, t = m.step(_base(abort_command=True))
    assert s == "ABORT" and t == "cruise_to_abort"


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({"quality_flag": 0.1}, id="quality_below_threshold"),
        pytest.param({"quality_flag": 1.0, "daidalus_alert": 2}, id="daidalus_amber_or_worse"),
    ],
)
def test_transition_to_event(extra: Dict[str, Any]) -> None:
    m = _fsm()
    m.seed("CRUISE")
    s, t = m.step(_base(**extra))
    assert s == "EVENT" and t == "to_event"


def test_transition_cruise_to_rtb() -> None:
    m = _fsm()
    m.seed("CRUISE")
    s, t = m.step(_base(rtb_command=True))
    assert s == "RTB" and t == "cruise_to_rtb"


def test_transition_to_landing() -> None:
    m = _fsm()
    m.seed("CRUISE")
    s, t = m.step(_base(land_command=True))
    assert s == "LANDING" and t == "to_landing"


def test_transition_event_to_cruise() -> None:
    m = _fsm()
    m.seed("EVENT")
    s, t = m.step(_base(event_cleared=True, quality_flag=0.2, daidalus_alert=2))
    assert s == "CRUISE" and t == "event_to_cruise"


def test_transition_event_to_abort() -> None:
    m = _fsm()
    m.seed("EVENT")
    s, t = m.step(_base(fdir_emergency=True, quality_flag=0.2, daidalus_alert=2))
    assert s == "ABORT" and t == "event_to_abort"


def test_transition_event_to_rtb() -> None:
    m = _fsm()
    m.seed("EVENT")
    s, t = m.step(_base(rtb_during_event=True, quality_flag=0.2, daidalus_alert=2))
    assert s == "RTB" and t == "event_to_rtb"


def test_transition_landing_to_goaround() -> None:
    m = _fsm()
    m.seed("LANDING")
    s, t = m.step(_base(approach_not_stabilized=True))
    assert s == "GO_AROUND" and t == "landing_to_goaround"


def test_transition_landing_complete() -> None:
    m = _fsm()
    m.seed("LANDING")
    s, t = m.step(_base(touchdown=True))
    assert s == "AUTOTAXI" and t == "landing_complete"


def test_transition_goaround_to_landing() -> None:
    m = _fsm()
    m.seed("GO_AROUND")
    s, t = m.step(_base(approach_not_stabilized=True, go_around_complete=True))
    assert s == "LANDING" and t == "goaround_to_landing"


def test_transition_goaround_to_cruise() -> None:
    m = _fsm()
    m.seed("GO_AROUND")
    s, t = m.step(_base(approach_not_stabilized=True, missed_approach_climb=True))
    assert s == "CRUISE" and t == "goaround_to_cruise"


def test_transition_abort_to_rtb() -> None:
    m = _fsm()
    m.seed("ABORT")
    s, t = m.step(_base(abort_command=True))
    assert s == "RTB" and t == "abort_to_rtb"


def test_transition_rtb_to_landing() -> None:
    m = _fsm()
    m.seed("RTB")
    s, t = m.step(_base(rtb_landing=True))
    assert s == "LANDING" and t == "rtb_to_landing"


def test_transition_rtb_to_cruise() -> None:
    m = _fsm()
    m.seed("RTB")
    s, t = m.step(_base(rtb_cancel=True))
    assert s == "CRUISE" and t == "rtb_to_cruise"
