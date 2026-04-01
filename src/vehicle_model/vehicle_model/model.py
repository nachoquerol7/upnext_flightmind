"""Fixed-wing vehicle envelope: speeds, turn radius, climb/descent, mass & fuel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, MutableMapping, Optional


@dataclass
class TrajectorySegment:
    """One segment check for `is_feasible` (positive climb = up, NED-safe for rates)."""

    speed_mps: float
    """Horizontal airspeed (m/s)."""
    climb_rate_mps: float
    """Positive = climbing (m/s upward)."""
    turn_radius_m: float = float("inf")
    """Horizontal turn radius (m); inf = straight."""


class VehicleModel:
    """Loads envelope parameters; tracks mass/fuel vs time; checks trajectories."""

    def __init__(
        self,
        v_min_ms: float,
        v_max_ms: float,
        turn_radius_min_m: float,
        climb_rate_max_ms: float,
        descent_rate_max_ms: float,
        glide_ratio: float,
        mtow_kg: float,
        fuel_burn_kgh: float,
        fuel_mass_initial_kg: float,
        v_min_reserve_gain_ms: float = 5.0,
    ) -> None:
        if v_min_ms <= 0 or v_max_ms <= v_min_ms:
            raise ValueError("invalid v_min_ms / v_max_ms")
        if turn_radius_min_m <= 0:
            raise ValueError("turn_radius_min_m must be positive")
        if climb_rate_max_ms <= 0 or descent_rate_max_ms <= 0:
            raise ValueError("climb/descent limits must be positive")
        if glide_ratio <= 0:
            raise ValueError("glide_ratio must be positive")
        if mtow_kg <= 0 or fuel_mass_initial_kg <= 0:
            raise ValueError("mass parameters must be positive")
        if fuel_mass_initial_kg > mtow_kg:
            raise ValueError("fuel_mass_initial_kg cannot exceed mtow_kg")
        if fuel_burn_kgh < 0:
            raise ValueError("fuel_burn_kgh must be non-negative")
        if v_min_reserve_gain_ms < 0:
            raise ValueError("v_min_reserve_gain_ms must be non-negative")

        self._v_min_base = float(v_min_ms)
        self.v_max_ms = float(v_max_ms)
        self.turn_radius_min_m = float(turn_radius_min_m)
        self.climb_rate_max_ms = float(climb_rate_max_ms)
        self.descent_rate_max_ms = float(descent_rate_max_ms)
        self.glide_ratio = float(glide_ratio)
        self.mtow_kg = float(mtow_kg)
        self.fuel_burn_kgh = float(fuel_burn_kgh)
        self.fuel_mass_initial_kg = float(fuel_mass_initial_kg)
        self._v_min_gain = float(v_min_reserve_gain_ms)

        self._dry_mass_kg = self.mtow_kg - self.fuel_mass_initial_kg
        self._elapsed_h = 0.0
        self._recompute_state()

    @classmethod
    def from_mapping(cls, m: Mapping[str, Any]) -> VehicleModel:
        return cls(
            v_min_ms=float(m["v_min_ms"]),
            v_max_ms=float(m["v_max_ms"]),
            turn_radius_min_m=float(m["turn_radius_min_m"]),
            climb_rate_max_ms=float(m["climb_rate_max_ms"]),
            descent_rate_max_ms=float(m["descent_rate_max_ms"]),
            glide_ratio=float(m["glide_ratio"]),
            mtow_kg=float(m["mtow_kg"]),
            fuel_burn_kgh=float(m["fuel_burn_kgh"]),
            fuel_mass_initial_kg=float(m.get("fuel_mass_initial_kg", 120.0)),
            v_min_reserve_gain_ms=float(m.get("v_min_reserve_gain_ms", 5.0)),
        )

    def _recompute_state(self) -> None:
        burned = self.fuel_burn_kgh * self._elapsed_h
        fuel_left = max(0.0, self.fuel_mass_initial_kg - burned)
        self._current_mass_kg = self._dry_mass_kg + fuel_left
        reserve_frac = fuel_left / self.fuel_mass_initial_kg if self.fuel_mass_initial_kg > 0 else 0.0
        # Less fuel remaining → higher minimum speed (conservative reserve policy).
        self._v_min_dynamic = self._v_min_base + self._v_min_gain * max(0.0, 1.0 - reserve_frac)

    def update_weight(self, elapsed_time_h: float) -> None:
        """Advance fuel burn by `elapsed_time_h` hours (absolute mission time from t0)."""
        self._elapsed_h = max(0.0, float(elapsed_time_h))
        self._recompute_state()

    @property
    def v_min_ms(self) -> float:
        return self._v_min_dynamic

    @property
    def current_mass_kg(self) -> float:
        return self._current_mass_kg

    @property
    def fuel_remaining_kg(self) -> float:
        return max(0.0, self.fuel_mass_initial_kg - self.fuel_burn_kgh * self._elapsed_h)

    def turn_radius_at_cruise_speed(self) -> float:
        """Minimum horizontal turn radius enforced at cruise (v_max)."""
        return self.turn_radius_min_m

    def is_feasible(self, trajectory: List[TrajectorySegment]) -> bool:
        """True if every segment respects speed, climb/descent, and turn radius."""
        for seg in trajectory:
            if seg.speed_mps < self._v_min_dynamic - 1e-9 or seg.speed_mps > self.v_max_ms + 1e-9:
                return False
            if seg.climb_rate_mps > self.climb_rate_max_ms + 1e-9:
                return False
            if seg.climb_rate_mps < -self.descent_rate_max_ms - 1e-9:
                return False
            if seg.turn_radius_m < self.turn_radius_min_m - 1e-9:
                return False
        return True

    def state_vector(self) -> List[float]:
        """Order matches `vehicle_model_node` publisher layout."""
        return [
            self._v_min_dynamic,
            self.v_max_ms,
            self.turn_radius_min_m,
            self.climb_rate_max_ms,
            self.descent_rate_max_ms,
            self.glide_ratio,
            self._current_mass_kg,
            self.fuel_remaining_kg,
        ]


def load_yaml_dict(path: str) -> MutableMapping[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        root = yaml.safe_load(f)
    if not isinstance(root, dict):
        raise ValueError("YAML root must be a mapping")
    node = root.get("vehicle_model_node", {})
    params = node.get("ros__parameters", {})
    if not isinstance(params, dict):
        raise ValueError("vehicle_model_node.ros__parameters missing")
    return params


def model_params_from_ros_dict(p: Mapping[str, Any]) -> MutableMapping[str, Any]:
    """Map ROS param names to VehicleModel constructor keys."""
    out: MutableMapping[str, Any] = {}
    keys = [
        "v_min_ms",
        "v_max_ms",
        "turn_radius_min_m",
        "climb_rate_max_ms",
        "descent_rate_max_ms",
        "glide_ratio",
        "mtow_kg",
        "fuel_burn_kgh",
        "fuel_mass_initial_kg",
        "v_min_reserve_gain_ms",
    ]
    for k in keys:
        if k in p:
            out[k] = p[k]
    return out
