"""PolyCARP-style geofence helpers: point-in-polygon and time-to-violation (NED NE plane)."""

from __future__ import annotations

import json
import math
from typing import List, Sequence, Tuple

Point = Tuple[float, float]
Polygon = Sequence[Point]


def point_in_polygon(n: float, e: float, polygon: Polygon) -> bool:
    """Ray casting; polygon vertices in order (n,e)."""
    if len(polygon) < 3:
        return False
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        ni, ei = float(polygon[i][0]), float(polygon[i][1])
        nj, ej = float(polygon[j][0]), float(polygon[j][1])
        if (ei > e) != (ej > e) and n < (nj - ni) * (e - ei) / (ej - ei + 1e-18) + ni:
            inside = not inside
        j = i
    return inside


def time_to_polygon_entry(
    n: float,
    e: float,
    vn: float,
    ve: float,
    polygon: Polygon,
    *,
    dt: float = 0.1,
    max_time_s: float = 600.0,
) -> float:
    """Time until position enters polygon along constant velocity; 0 if inside; inf if no entry."""
    if len(polygon) < 3:
        return float("inf")
    if point_in_polygon(n, e, polygon):
        return 0.0
    if math.hypot(vn, ve) < 1e-9:
        return float("inf")
    t = 0.0
    while t <= max_time_s:
        if point_in_polygon(n + vn * t, e + ve * t, polygon):
            return t
        t += dt
    return float("inf")


def parse_geofences_json(s: str) -> List[Polygon]:
    """JSON: {\"polygons\": [[[n,e],...], ...]}."""
    if not s or not s.strip():
        return []
    data = json.loads(s)
    polys: List[Polygon] = []
    raw = data.get("polygons", [])
    if not isinstance(raw, list):
        return []
    for p in raw:
        if isinstance(p, list) and len(p) >= 3:
            polys.append(tuple((float(q[0]), float(q[1])) for q in p))
    return polys


def evaluate_geofence_threat(
    n: float,
    e: float,
    vn: float,
    ve: float,
    polygons: Sequence[Polygon],
    *,
    imminent_horizon_s: float = 60.0,
) -> Tuple[bool, float]:
    """(violation_imminent, time_to_violation). min time across polygons."""
    if not polygons:
        return False, float("inf")
    min_t = float("inf")
    inside_any = False
    for poly in polygons:
        if point_in_polygon(n, e, poly):
            inside_any = True
            min_t = 0.0
            break
        t = time_to_polygon_entry(n, e, vn, ve, poly)
        min_t = min(min_t, t)
    imminent = inside_any or (math.isfinite(min_t) and min_t <= imminent_horizon_s)
    return imminent, min_t
