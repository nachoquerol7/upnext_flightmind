"""Waypoint sequencing + reach detection (TRAJ-007, TRAJ-009, TRAJ-010)."""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple


def ned_distance(a: Sequence[float], b: Sequence[float]) -> float:
    dn = float(a[0]) - float(b[0])
    de = float(a[1]) - float(b[1])
    dd = float(a[2]) - float(b[2])
    return math.sqrt(dn * dn + de * de + dd * dd)


def path_to_ned_waypoints(path_poses) -> List[Tuple[float, float, float]]:
    out: List[Tuple[float, float, float]] = []
    for ps in path_poses:
        p = ps.pose.position
        out.append((float(p.x), float(p.y), float(p.z)))
    return out


class WaypointFollower:
    """Holds waypoint list, index, radius; advances on reach; signals mission end."""

    def __init__(self, waypoint_radius_m: float = 5.0) -> None:
        self.waypoint_radius_m = waypoint_radius_m
        self.waypoints: List[Tuple[float, float, float]] = []
        self.wp_idx = 0

    def set_path(self, wps: List[Tuple[float, float, float]]) -> None:
        self.waypoints = list(wps)
        self.wp_idx = 0

    def current_target(self) -> Optional[Tuple[float, float, float]]:
        if not self.waypoints or self.wp_idx >= len(self.waypoints):
            return None
        return self.waypoints[self.wp_idx]

    def step(
        self, position_ned: Sequence[float], _cruise_speed_ms: float
    ) -> Tuple[Optional[Tuple[float, float, float]], Optional[float], bool]:
        """Returns (target_ned or None, distance_to_target or None, mission_complete)."""
        if self.wp_idx >= len(self.waypoints):
            return None, None, True
        tgt = self.waypoints[self.wp_idx]
        dist = ned_distance(position_ned, tgt)
        if dist < self.waypoint_radius_m:
            self.wp_idx += 1
            if self.wp_idx >= len(self.waypoints):
                return None, dist, True
            tgt = self.waypoints[self.wp_idx]
            dist = ned_distance(position_ned, tgt)
        return tgt, dist, False

    def velocity_toward(self, position_ned: Sequence[float], cruise_speed_ms: float) -> Tuple[float, float, float]:
        tgt = self.current_target()
        if tgt is None:
            return (0.0, 0.0, 0.0)
        dn = tgt[0] - float(position_ned[0])
        de = tgt[1] - float(position_ned[1])
        norm = math.hypot(dn, de) + 1e-9
        s = cruise_speed_ms / norm
        return (dn * s, de * s, 0.0)
