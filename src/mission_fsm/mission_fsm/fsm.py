"""Mission FSM: YAML-defined states, entry guards, and ordered transitions."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Tuple, Union

Condition = Union[str, Mapping[str, Any]]
Inputs = MutableMapping[str, Any]
Context = Mapping[str, Any]


def _builtin_quality_degraded(i: Inputs, c: Context) -> bool:
    return float(i.get("quality_flag", 1.0)) < float(c["quality_flag_threshold"])


def _builtin_daidalus_escalated(i: Inputs, c: Context) -> bool:
    return int(i.get("daidalus_alert", 0)) >= int(c["daidalus_alert_amber"])


def _builtin_fdir_emergency(i: Inputs, c: Context) -> bool:
    return bool(i.get("fdir_emergency", False))


def _builtin_approach_unstabilized(i: Inputs, c: Context) -> bool:
    return bool(i.get("approach_not_stabilized", False))


BUILTINS: Dict[str, Callable[[Inputs, Context], bool]] = {
    "quality_degraded": _builtin_quality_degraded,
    "daidalus_escalated": _builtin_daidalus_escalated,
    "fdir_emergency": _builtin_fdir_emergency,
    "approach_not_stabilized": _builtin_approach_unstabilized,
}


def eval_condition(cond: Any, inputs: Inputs, ctx: Context) -> bool:
    """Evaluate YAML condition tree or atomic name."""
    if cond is None or cond == {}:
        return True
    if isinstance(cond, str):
        if cond in BUILTINS:
            return BUILTINS[cond](inputs, ctx)
        if cond in inputs:
            v = inputs[cond]
            if isinstance(v, bool):
                return v
            return bool(v)
        raise KeyError(f"unknown condition atom: {cond!r}")
    if not isinstance(cond, Mapping):
        raise TypeError(f"invalid condition type: {type(cond)}")
    if "all" in cond:
        return all(eval_condition(x, inputs, ctx) for x in cond["all"])
    if "any" in cond:
        return any(eval_condition(x, inputs, ctx) for x in cond["any"])
    if "not" in cond:
        return not eval_condition(cond["not"], inputs, ctx)
    raise KeyError(f"unknown condition keys: {cond.keys()}")


def default_inputs() -> Dict[str, Any]:
    return {
        "quality_flag": 1.0,
        "daidalus_alert": 0,
        "fdir_emergency": False,
        "approach_not_stabilized": False,
        "preflight_ok": False,
        "taxi_clear": False,
        "takeoff_complete": False,
        "land_command": False,
        "rtb_command": False,
        "abort_command": False,
        "event_cleared": False,
        "rtb_during_event": False,
        "touchdown": False,
        "go_around_complete": False,
        "missed_approach_climb": False,
        "abort_rtb_ack": False,
        "rtb_landing": False,
        "rtb_cancel": False,
    }


class MissionFsm:
    """Finite-state machine with first-match transition ordering per source state."""

    def __init__(
        self,
        *,
        initial_state: str,
        context: Mapping[str, Any],
        state_entry: Mapping[str, Any],
        transitions: List[Mapping[str, Any]],
    ) -> None:
        self._initial_state = initial_state
        self._state = initial_state
        self._context = dict(context)
        self._entry: Dict[str, Any] = {k: v for k, v in state_entry.items()}
        self._transitions: List[Mapping[str, Any]] = list(transitions)
        states = set(self._entry.keys())
        for t in self._transitions:
            states.add(str(t["from"]))
            states.add(str(t["to"]))
        for s in states:
            self._entry.setdefault(s, {})

    @property
    def state(self) -> str:
        return self._state

    @classmethod
    def from_fsm_yaml(
        cls,
        root: Mapping[str, Any],
        *,
        parameter_overlay: Optional[Mapping[str, Any]] = None,
    ) -> MissionFsm:
        fsm = root.get("fsm")
        if not isinstance(fsm, dict):
            raise ValueError("fsm root missing")
        states = fsm.get("states")
        trans = fsm.get("transitions")
        if not isinstance(states, dict) or not isinstance(trans, list):
            raise ValueError("fsm.states (map) and fsm.transitions (list) required")

        params = root.get("mission_fsm_node", {})
        ros_params = params.get("ros__parameters", {}) if isinstance(params, dict) else {}
        if not isinstance(ros_params, dict):
            ros_params = {}
        ctx: Dict[str, Any] = {
            "quality_flag_threshold": float(ros_params.get("quality_flag_threshold", 0.5)),
            "daidalus_alert_amber": int(ros_params.get("daidalus_alert_amber", 1)),
        }
        if parameter_overlay:
            for k, v in parameter_overlay.items():
                if k == "quality_flag_threshold":
                    ctx[k] = float(v)
                elif k == "daidalus_alert_amber":
                    ctx[k] = int(v)
                else:
                    ctx[k] = v

        initial = str(ros_params.get("initial_state", "PREFLIGHT"))

        entry: Dict[str, Any] = {}
        for name, spec in states.items():
            if not isinstance(spec, dict):
                raise ValueError(f"state {name} must be a mapping")
            g = spec.get("entry_guards", {})
            entry[str(name)] = g if g else {}

        return cls(initial_state=initial, context=ctx, state_entry=entry, transitions=trans)

    def step(self, inputs: Mapping[str, Any]) -> Tuple[str, Optional[str]]:
        """Apply first matching transition from current state; return (state, trigger_or_none)."""
        merged: Inputs = {**default_inputs(), **inputs}
        fired: Optional[str] = None
        for t in self._transitions:
            if str(t["from"]) != self._state:
                continue
            when = t.get("when", {})
            target = str(t["to"])
            trigger = str(t.get("trigger", t.get("name", "")))
            if not eval_condition(when, merged, self._context):
                continue
            entry_guard = self._entry.get(target, {})
            if not eval_condition(entry_guard, merged, self._context):
                continue
            self._state = target
            fired = trigger or None
            break
        return self._state, fired

    def seed(self, state: str) -> None:
        """Set current state (for tests or operator override)."""
        self._state = str(state)

    def reset(self, state: Optional[str] = None) -> None:
        self._state = state if state is not None else self._initial_state


def load_fsm_yaml_dict(path: str) -> MutableMapping[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    return data


def mission_fsm_from_path(path: str, **kwargs: Any) -> MissionFsm:
    return MissionFsm.from_fsm_yaml(load_fsm_yaml_dict(path), **kwargs)
