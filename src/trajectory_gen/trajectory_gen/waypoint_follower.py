"""Waypoint sequencing, Pure Pursuit on resampled nav_msgs polylines (TRAJ-007..010)."""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple


def path_to_ned_waypoints(path_poses) -> List[Tuple[float, float, float]]:
    """Extrae (north, east, down) desde poses nav_msgs/Path."""
    out: List[Tuple[float, float, float]] = []
    for ps in path_poses:
        p = ps.pose.position
        out.append((float(p.x), float(p.y), float(p.z)))
    return out


def ned_distance(a: Sequence[float], b: Sequence[float]) -> float:
    dn = float(a[0]) - float(b[0])
    de = float(a[1]) - float(b[1])
    dd = float(a[2]) - float(b[2])
    return math.sqrt(dn * dn + de * de + dd * dd)


def _dot3(
    ax: float, ay: float, az: float, bx: float, by: float, bz: float
) -> float:
    return ax * bx + ay * by + az * bz


def resample_polyline(
    points: List[Tuple[float, float, float]], step_m: float
) -> List[Tuple[float, float, float]]:
    """Densifica la polilínea NED con muestras cada ~step_m de longitud de arco."""
    if len(points) < 2:
        return list(points)
    step = max(0.05, float(step_m))
    seg_lens: List[float] = []
    for i in range(len(points) - 1):
        seg_lens.append(ned_distance(points[i], points[i + 1]))
    total = sum(seg_lens)
    if total < 1e-6:
        return [points[0], points[-1]]
    out: List[Tuple[float, float, float]] = []
    s = 0.0
    while s <= total + 1e-6:
        acc = 0.0
        placed = False
        for i, L in enumerate(seg_lens):
            if L < 1e-9:
                continue
            if acc + L >= s - 1e-9:
                t = (s - acc) / L
                t = max(0.0, min(1.0, t))
                a = points[i]
                b = points[i + 1]
                out.append(
                    (
                        a[0] + t * (b[0] - a[0]),
                        a[1] + t * (b[1] - a[1]),
                        a[2] + t * (b[2] - a[2]),
                    )
                )
                placed = True
                break
            acc += L
        if not placed:
            out.append(points[-1])
            break
        s += step
    if not out or ned_distance(out[-1], points[-1]) > 0.05:
        out.append(points[-1])
    # Elimina duplicados casi idénticos
    dedup: List[Tuple[float, float, float]] = []
    for p in out:
        if not dedup or ned_distance(dedup[-1], p) > 1e-3:
            dedup.append(p)
    return dedup


def _closest_point_on_polyline(
    position_ned: Sequence[float], poly: List[Tuple[float, float, float]]
) -> Tuple[float, int, float]:
    """Devuelve (distancia al punto más cercano, índice de vértice de inicio del segmento, s a lo largo de la polilínea)."""
    qx, qy, qz = float(position_ned[0]), float(position_ned[1]), float(position_ned[2])
    best_d2 = float("inf")
    best_s = 0.0
    best_seg = 0
    cum = 0.0
    for i in range(len(poly) - 1):
        ax, ay, az = poly[i]
        bx, by, bz = poly[i + 1]
        abx, aby, abz = bx - ax, by - ay, bz - az
        lab2 = _dot3(abx, aby, abz, abx, aby, abz)
        if lab2 < 1e-12:
            px, py, pz = ax, ay, az
            t = 0.0
        else:
            aqx, aqy, aqz = qx - ax, qy - ay, qz - az
            t = max(0.0, min(1.0, _dot3(aqx, aqy, aqz, abx, aby, abz) / lab2))
            px = ax + t * abx
            py = ay + t * aby
            pz = az + t * abz
        dx, dy, dz = qx - px, qy - py, qz - pz
        d2 = dx * dx + dy * dy + dz * dz
        seg_len = math.sqrt(lab2) if lab2 >= 1e-12 else 0.0
        s_here = cum + t * seg_len
        if d2 < best_d2:
            best_d2 = d2
            best_s = s_here
            best_seg = i
        cum += seg_len
    return math.sqrt(best_d2), best_seg, best_s


def _point_at_arc_length(
    poly: List[Tuple[float, float, float]], s_target: float
) -> Tuple[float, float, float]:
    if not poly:
        return (0.0, 0.0, 0.0)
    if s_target <= 0.0:
        return poly[0]
    cum = 0.0
    for i in range(len(poly) - 1):
        a = poly[i]
        b = poly[i + 1]
        L = ned_distance(a, b)
        if L < 1e-9:
            continue
        if cum + L >= s_target - 1e-9:
            t = (s_target - cum) / L
            t = max(0.0, min(1.0, t))
            return (
                a[0] + t * (b[0] - a[0]),
                a[1] + t * (b[1] - a[1]),
                a[2] + t * (b[2] - a[2]),
            )
        cum += L
    return poly[-1]


class WaypointFollower:
    """Modo legacy: índice de waypoint + radio. Modo Pure Pursuit: look-ahead sobre polilínea remuestreada."""

    def __init__(
        self,
        waypoint_radius_m: float = 5.0,
        *,
        use_pure_pursuit: bool = False,
        pure_pursuit_lookahead_m: float = 2.5,
        path_resample_step_m: float = 0.5,
        arrival_radius_m: float = 2.0,
    ) -> None:
        self.waypoint_radius_m = float(waypoint_radius_m)
        self.use_pure_pursuit = bool(use_pure_pursuit)
        self.pure_pursuit_lookahead_m = float(
            min(3.0, max(2.0, pure_pursuit_lookahead_m))
        )
        self.path_resample_step_m = float(path_resample_step_m)
        self.arrival_radius_m = float(arrival_radius_m)
        self.waypoints: List[Tuple[float, float, float]] = []
        self.wp_idx = 0
        self._poly: List[Tuple[float, float, float]] = []
        self._poly_len = 0.0

    def progress_fragment(self) -> str:
        if self.use_pure_pursuit:
            return f"pp:{len(self._poly)} seg0:{self.wp_idx}"
        return f"wp:{self.wp_idx}/{max(1, len(self.waypoints))}"

    def set_path(self, wps: List[Tuple[float, float, float]]) -> None:
        self.waypoints = list(wps)
        self.wp_idx = 0
        if self.use_pure_pursuit and len(self.waypoints) >= 2:
            self._poly = resample_polyline(self.waypoints, self.path_resample_step_m)
        elif self.use_pure_pursuit and len(self.waypoints) == 1:
            self._poly = list(self.waypoints)
        else:
            self._poly = []
        if len(self._poly) >= 2:
            acc = 0.0
            for i in range(len(self._poly) - 1):
                acc += ned_distance(self._poly[i], self._poly[i + 1])
            self._poly_len = acc
        else:
            self._poly_len = 0.0

    def current_target(self) -> Optional[Tuple[float, float, float]]:
        if self.use_pure_pursuit:
            # Sin posición del vehículo no hay look-ahead; usar último punto como fallback.
            return self._poly[-1] if self._poly else None
        if not self.waypoints or self.wp_idx >= len(self.waypoints):
            return None
        return self.waypoints[self.wp_idx]

    def step(
        self, position_ned: Sequence[float], _cruise_speed_ms: float
    ) -> Tuple[Optional[Tuple[float, float, float]], Optional[float], bool]:
        if self.use_pure_pursuit:
            return self._step_pure_pursuit(position_ned)
        return self._step_legacy(position_ned)

    def _step_legacy(
        self, position_ned: Sequence[float]
    ) -> Tuple[Optional[Tuple[float, float, float]], Optional[float], bool]:
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

    def _step_pure_pursuit(
        self, position_ned: Sequence[float]
    ) -> Tuple[Optional[Tuple[float, float, float]], Optional[float], bool]:
        if len(self._poly) < 2:
            if len(self._poly) == 1:
                d = ned_distance(position_ned, self._poly[0])
                done = d < self.arrival_radius_m
                return self._poly[0], d, done
            return None, None, True

        _, _seg, s_close = _closest_point_on_polyline(position_ned, self._poly)
        self.wp_idx = min(len(self._poly) - 2, max(0, _seg))
        s_goal = min(s_close + self.pure_pursuit_lookahead_m, self._poly_len)
        la = _point_at_arc_length(self._poly, s_goal)
        dist = ned_distance(position_ned, la)
        end_pt = self._poly[-1]
        at_end = s_goal >= self._poly_len - 0.05 and ned_distance(position_ned, end_pt) < self.arrival_radius_m
        if at_end:
            return None, dist, True
        return la, dist, False

    def velocity_toward(
        self, position_ned: Sequence[float], cruise_speed_ms: float
    ) -> Tuple[float, float, float]:
        if self.use_pure_pursuit and len(self._poly) >= 2:
            _, _, s_close = _closest_point_on_polyline(position_ned, self._poly)
            s_goal = min(s_close + self.pure_pursuit_lookahead_m, self._poly_len)
            tgt = _point_at_arc_length(self._poly, s_goal)
        elif self.use_pure_pursuit and len(self._poly) == 1:
            tgt = self._poly[0]
        else:
            tgt = self.current_target()
        if tgt is None:
            return (0.0, 0.0, 0.0)
        dn = tgt[0] - float(position_ned[0])
        de = tgt[1] - float(position_ned[1])
        dd = tgt[2] - float(position_ned[2])
        norm = math.sqrt(dn * dn + de * de + dd * dd) + 1e-9
        s = cruise_speed_ms / norm
        return (dn * s, de * s, dd * s)
