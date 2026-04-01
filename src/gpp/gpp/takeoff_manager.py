"""Takeoff phase manager: GROUND → ROTATE → CLIMB → CRUISE (or ABORT)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TakeoffConfig:
    vr_mps: float = 28.0
    climb_rate_max_mps: float = 8.0
    pitch_max_deg: float = 12.0
    decel_mps2: float = 2.5
    rotate_threshold: float = 0.95
    liftoff_alt_m: float = 5.0
    cruise_alt_agl_m: float = 150.0


class TakeoffManager:
    """Abort if runway remaining < braking distance at current speed."""

    def __init__(self, cfg: TakeoffConfig | None = None) -> None:
        self.cfg = cfg or TakeoffConfig()
        self._phase = "GROUND"
        self._commanded_climb_mps = 0.0

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def commanded_climb_mps(self) -> float:
        return self._commanded_climb_mps

    @staticmethod
    def braking_distance_m(airspeed_mps: float, decel_mps2: float) -> float:
        a = max(decel_mps2, 1e-6)
        return (airspeed_mps * airspeed_mps) / (2.0 * a)

    def reset(self) -> None:
        self._phase = "GROUND"
        self._commanded_climb_mps = 0.0

    def update(
        self,
        airspeed_mps: float,
        runway_remaining_m: float,
        altitude_agl_m: float,
        vertical_speed_up_mps: float,
        *,
        desired_climb_mps: float = 6.0,
    ) -> str:
        if self._phase == "ABORT":
            return self._phase

        bd = self.braking_distance_m(airspeed_mps, self.cfg.decel_mps2)
        if runway_remaining_m < bd and self._phase in ("GROUND", "ROTATE"):
            self._phase = "ABORT"
            self._commanded_climb_mps = 0.0
            return self._phase

        if self._phase == "GROUND":
            if airspeed_mps >= self.cfg.vr_mps * self.cfg.rotate_threshold:
                self._phase = "ROTATE"
        elif self._phase == "ROTATE":
            if altitude_agl_m >= self.cfg.liftoff_alt_m:
                self._phase = "CLIMB"
        elif self._phase == "CLIMB":
            _ = vertical_speed_up_mps
            self._commanded_climb_mps = min(
                max(0.0, desired_climb_mps), self.cfg.climb_rate_max_mps
            )
            if altitude_agl_m >= self.cfg.cruise_alt_agl_m:
                self._phase = "CRUISE"
                self._commanded_climb_mps = 0.0
        elif self._phase == "CRUISE":
            self._commanded_climb_mps = 0.0

        return self._phase
