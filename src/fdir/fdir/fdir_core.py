"""Pure FDIR logic (no ROS). Used by fdir_node and pytest."""

from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres (WGS84 sphere)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


@dataclass
class FdirConfig:
    nav_mild_below: float = 0.65
    nav_severe_below: float = 0.35
    nav_critical_below: float = 0.15
    motor_loss_window_s: float = 2.0
    motor_loss_throttle_min: float = 0.35
    motor_loss_vertical_accel_max_m_s2: float = -1.5
    sensor_timeout_nav_quality_s: float = 3.0
    c2_heartbeat_timeout_s: float = 1.5
    link_loss_hold_s: float = 30.0
    link_loss_land_s: float = 120.0
    glide_ratio: float = 18.0
    emergency_zones: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, m: Dict[str, Any]) -> FdirConfig:
        z = m.get("emergency_landing_zones")
        zones = list(z) if isinstance(z, list) else []
        return cls(
            nav_mild_below=float(m.get("nav_mild_below", 0.65)),
            nav_severe_below=float(m.get("nav_severe_below", 0.35)),
            nav_critical_below=float(m.get("nav_critical_below", 0.15)),
            motor_loss_window_s=float(m.get("motor_loss_window_s", 2.0)),
            motor_loss_throttle_min=float(m.get("motor_loss_throttle_min", 0.35)),
            motor_loss_vertical_accel_max_m_s2=float(m.get("motor_loss_vertical_accel_max_m_s2", -1.5)),
            sensor_timeout_nav_quality_s=float(m.get("sensor_timeout_nav_quality_s", 3.0)),
            c2_heartbeat_timeout_s=float(m.get("c2_heartbeat_timeout_s", 1.5)),
            link_loss_hold_s=float(m.get("link_loss_hold_s", 30.0)),
            link_loss_land_s=float(m.get("link_loss_land_s", 120.0)),
            glide_ratio=float(m.get("glide_ratio", 18.0)),
            emergency_zones=zones,
        )


@dataclass
class FdirSnapshot:
    time_sec: float
    quality_flag: Optional[float]
    last_quality_rx_time: Optional[float]
    c2_heartbeat_last_rx: Optional[float]
    throttle_commanded: float
    vertical_accel_m_s2: float
    armed: bool
    failure_motor_px4: bool
    fsm_mode: str
    vehicle_lat: float
    vehicle_lon: float
    vehicle_altitude_amsl_m: float


@dataclass
class FdirOutputs:
    active_fault: str
    policy_action: str
    emergency_landing_target_json: str


class FdirEngine:
    """Priority: sensor timeout → motor loss → link loss → nav degraded."""

    def __init__(self, cfg: FdirConfig) -> None:
        self.cfg = cfg
        self._motor_samples: Deque[Tuple[float, float, float]] = deque()

    def reset(self) -> None:
        self._motor_samples.clear()

    def _trim_motor(self, now: float) -> None:
        w = self.cfg.motor_loss_window_s
        while self._motor_samples and self._motor_samples[0][0] < now - w:
            self._motor_samples.popleft()

    def _motor_loss(self, snap: FdirSnapshot) -> bool:
        if not snap.armed:
            return False
        if snap.failure_motor_px4:
            return True
        self._trim_motor(snap.time_sec)
        self._motor_samples.append(
            (snap.time_sec, snap.throttle_commanded, snap.vertical_accel_m_s2)
        )
        self._trim_motor(snap.time_sec)
        if not self._motor_samples:
            return False
        oldest = self._motor_samples[0][0]
        if snap.time_sec - oldest < self.cfg.motor_loss_window_s - 1e-6:
            return False
        for _, thr, vacc in self._motor_samples:
            if thr <= self.cfg.motor_loss_throttle_min:
                return False
            if vacc >= self.cfg.motor_loss_vertical_accel_max_m_s2:
                return False
        return True

    def _link_policy(self, snap: FdirSnapshot) -> Optional[str]:
        """Return HOLD, RTB, LAND_BEST_AVAILABLE or None if link OK / unknown."""
        if snap.c2_heartbeat_last_rx is None:
            return None
        elapsed = snap.time_sec - snap.c2_heartbeat_last_rx
        if elapsed <= self.cfg.c2_heartbeat_timeout_s:
            return None
        if elapsed <= self.cfg.link_loss_hold_s:
            return "HOLD"
        if elapsed <= self.cfg.link_loss_land_s:
            return "RTB"
        return "LAND_BEST_AVAILABLE"

    def pick_emergency_zone(self, snap: FdirSnapshot) -> Optional[Dict[str, Any]]:
        alt = max(0.0, float(snap.vehicle_altitude_amsl_m))
        reach = self.cfg.glide_ratio * alt
        candidates: List[Dict[str, Any]] = []
        for z in self.cfg.emergency_zones:
            lat, lon = float(z["lat"]), float(z["lon"])
            dist = haversine_m(snap.vehicle_lat, snap.vehicle_lon, lat, lon)
            if dist <= reach + 1.0:
                row = {
                    "lat": lat,
                    "lon": lon,
                    "longitud_pista": float(z.get("longitud_pista", 0.0)),
                    "calidad": float(z.get("calidad", 0.0)),
                    "distance_m": dist,
                    "reachable": True,
                    "glide_distance_available_m": reach,
                }
                candidates.append(row)
        if not candidates:
            return None
        candidates.sort(key=lambda r: (-r["calidad"], r["distance_m"]))
        return candidates[0]

    def evaluate(self, snap: FdirSnapshot) -> FdirOutputs:
        if snap.last_quality_rx_time is None:
            return FdirOutputs("SENSOR_TIMEOUT", "HOLD", "")
        if snap.time_sec - snap.last_quality_rx_time > self.cfg.sensor_timeout_nav_quality_s:
            return FdirOutputs("SENSOR_TIMEOUT", "HOLD", "")

        if self._motor_loss(snap):
            zone = self.pick_emergency_zone(snap)
            payload = zone if zone else {"reachable": False, "reason": "no_zone_in_glide_range"}
            return FdirOutputs("MOTOR_LOSS", "GLIDE_EMERGENCY_TARGET", json.dumps(payload))

        lp = self._link_policy(snap)
        if lp == "HOLD":
            return FdirOutputs("LINK_LOSS", "HOLD", "")
        if lp == "RTB":
            return FdirOutputs("LINK_LOSS", "RTB", "")
        if lp == "LAND_BEST_AVAILABLE":
            zone = self.pick_emergency_zone(snap)
            payload = zone if zone else {"reachable": False, "reason": "land_best_available_no_zone"}
            return FdirOutputs("LINK_LOSS", "LAND_BEST_AVAILABLE", json.dumps(payload))

        q = snap.quality_flag
        if q is None:
            return FdirOutputs("NONE", "NONE", "")
        if q < self.cfg.nav_critical_below:
            return FdirOutputs("NAV_DEGRADED", "RTB", "")
        if q < self.cfg.nav_severe_below:
            return FdirOutputs("NAV_DEGRADED", "HOLD", "")
        if q < self.cfg.nav_mild_below:
            return FdirOutputs("NAV_DEGRADED", "WIDEN_MARGINS_REDUCE_SPEED", "")

        return FdirOutputs("NONE", "NONE", "")


def load_fdir_yaml(path: str) -> Dict[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        root = yaml.safe_load(f)
    if not isinstance(root, dict):
        raise ValueError("YAML root must be mapping")
    return root


def config_from_yaml_root(root: Dict[str, Any]) -> FdirConfig:
    params = root.get("fdir_node", {}).get("ros__parameters", {})
    if not isinstance(params, dict):
        params = {}
    zones = root.get("emergency_landing_zones", [])
    if not isinstance(zones, list):
        zones = []
    merged = {**params, "emergency_landing_zones": zones}
    return FdirConfig.from_mapping(merged)
