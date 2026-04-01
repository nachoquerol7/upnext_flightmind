"""Mission FSM: YAML-defined states, entry guards, and ordered transitions."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Tuple, Union

Condition = Union[str, Mapping[str, Any]]
Inputs = MutableMapping[str, Any]
Context = Mapping[str, Any]


def _builtin_fdir_emergency(i: Inputs, c: Context) -> bool:
    return bool(i.get("fdir_emergency", False))


def _builtin_approach_unstabilized(i: Inputs, c: Context) -> bool:
    return bool(i.get("approach_not_stabilized", False))


def _builtin_daidalus_near(i: Inputs, c: Context) -> bool:
    return int(i.get("daidalus_alert", 0)) == 3


def _builtin_daidalus_recovery(i: Inputs, c: Context) -> bool:
    return int(i.get("daidalus_alert", 0)) >= 4


BUILTINS: Dict[str, Callable[[Inputs, Context], bool]] = {
    "fdir_emergency": _builtin_fdir_emergency,
    "approach_not_stabilized": _builtin_approach_unstabilized,
    "daidalus_near": _builtin_daidalus_near,
    "daidalus_recovery": _builtin_daidalus_recovery,
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
        "quality_degraded": False,
        "quality_recovered": False,
        "daidalus_escalated": False,
        "state_dwell_timeout": False,
        "daidalus_feed_lost": False,
        "gcs_lost": False,
        "c2_lost": False,
        "battery_low": False,
        "geofence_violation": False,
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
        max_duration_by_state: Optional[Mapping[str, float]] = None,
    ) -> None:
        self._initial_state = initial_state
        self._state = initial_state
        self._context = dict(context)
        self._entry: Dict[str, Any] = {k: v for k, v in state_entry.items()}
        self._transitions: List[Mapping[str, Any]] = list(transitions)
        self._max_duration_by_state: Dict[str, float] = dict(max_duration_by_state or {})
        self._ticks_in_state = 0
        self._quality_low_streak = 0
        self._quality_high_streak = 0
        self._daidalus_mid_streak = 0
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
            "tick_hz": float(ros_params.get("tick_hz", 10.0)),
            "hysteresis_ticks_on": int(ros_params.get("hysteresis_ticks_on", 3)),
            "hysteresis_ticks_off": int(ros_params.get("hysteresis_ticks_off", 5)),
            "hysteresis_margin": float(ros_params.get("hysteresis_margin", 0.05)),
            "daidalus_escalate_ticks": int(ros_params.get("daidalus_escalate_ticks", 2)),
        }
        if parameter_overlay:
            for k, v in parameter_overlay.items():
                if k in (
                    "quality_flag_threshold",
                    "hysteresis_margin",
                    "tick_hz",
                ):
                    ctx[k] = float(v)
                elif k in (
                    "daidalus_alert_amber",
                    "hysteresis_ticks_on",
                    "hysteresis_ticks_off",
                    "daidalus_escalate_ticks",
                ):
                    ctx[k] = int(v)
                else:
                    ctx[k] = v

        initial = str(ros_params.get("initial_state", "PREFLIGHT"))

        entry: Dict[str, Any] = {}
        max_dur: Dict[str, float] = {}
        for name, spec in states.items():
            if not isinstance(spec, dict):
                raise ValueError(f"state {name} must be a mapping")
            g = spec.get("entry_guards", {})
            entry[str(name)] = g if g else {}
            if "max_duration_sec" in spec:
                max_dur[str(name)] = float(spec["max_duration_sec"])

        return cls(
            initial_state=initial,
            context=ctx,
            state_entry=entry,
            transitions=trans,
            max_duration_by_state=max_dur,
        )

    def _update_quality_hysteresis(self, merged: Inputs) -> None:
        q = float(merged.get("quality_flag", 1.0))
        th = float(self._context["quality_flag_threshold"])
        margin = float(self._context.get("hysteresis_margin", 0.05))
        if q < th:
            self._quality_low_streak += 1
            self._quality_high_streak = 0
        elif q > th + margin:
            self._quality_high_streak += 1
            self._quality_low_streak = 0
        else:
            self._quality_low_streak = 0
            self._quality_high_streak = 0

    def _update_daidalus_mid_streak(self, merged: Inputs) -> None:
        a = int(merged.get("daidalus_alert", 0))
        amber = int(self._context.get("daidalus_alert_amber", 1))
        if amber <= a <= 2:
            self._daidalus_mid_streak += 1
        else:
            self._daidalus_mid_streak = 0

    def _quality_degraded_effective(self) -> bool:
        n_on = int(self._context.get("hysteresis_ticks_on", 3))
        return self._quality_low_streak >= n_on

    def _quality_recovered_effective(self) -> bool:
        n_off = int(self._context.get("hysteresis_ticks_off", 5))
        return self._quality_high_streak >= n_off

    def _daidalus_escalated_effective(self, merged: Inputs) -> bool:
        a = int(merged.get("daidalus_alert", 0))
        amber = int(self._context.get("daidalus_alert_amber", 1))
        need = int(self._context.get("daidalus_escalate_ticks", 2))
        if a >= 3:
            return False
        if a >= amber:
            return self._daidalus_mid_streak >= need
        return False

    def _reset_hysteresis_streaks(self) -> None:
        self._quality_low_streak = 0
        self._quality_high_streak = 0
        self._daidalus_mid_streak = 0

    def step(self, inputs: Mapping[str, Any]) -> Tuple[str, Optional[str]]:
        """Apply first matching transition from current state; return (state, trigger_or_none)."""
        merged: Inputs = {**default_inputs(), **inputs}

        max_d = self._max_duration_by_state.get(self._state)
        self._ticks_in_state += 1
        tick_hz = float(self._context.get("tick_hz", 10.0))
        if tick_hz < 1e-6:
            tick_hz = 10.0
        elapsed = self._ticks_in_state / tick_hz
        merged["state_dwell_timeout"] = bool(max_d is not None and elapsed >= float(max_d))

        self._update_quality_hysteresis(merged)
        self._update_daidalus_mid_streak(merged)
        merged["quality_degraded"] = self._quality_degraded_effective()
        merged["quality_recovered"] = self._quality_recovered_effective()
        merged["daidalus_escalated"] = self._daidalus_escalated_effective(merged)

        prev_state = self._state
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
        if self._state != prev_state:
            self._ticks_in_state = 0
            self._reset_hysteresis_streaks()
        return self._state, fired

    def seed(self, state: str) -> None:
        """Set current state (for tests or operator override)."""
        self._state = str(state)
        self._ticks_in_state = 0
        self._reset_hysteresis_streaks()

    def reset(self, state: Optional[str] = None) -> None:
        self._state = state if state is not None else self._initial_state
        self._ticks_in_state = 0
        self._reset_hysteresis_streaks()


def load_fsm_yaml_dict(path: str) -> MutableMapping[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    return data


def mission_fsm_from_path(path: str, **kwargs: Any) -> MissionFsm:
    return MissionFsm.from_fsm_yaml(load_fsm_yaml_dict(path), **kwargs)
