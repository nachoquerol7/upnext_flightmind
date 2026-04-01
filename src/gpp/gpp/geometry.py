"""NED NE plane geometry (NFZ / collision)."""

from __future__ import annotations

import json
import math
from typing import List, Sequence, Tuple

Point = Tuple[float, float]
Polygon = Sequence[Point]


def point_in_polygon(n: float, e: float, polygon: Polygon) -> bool:
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


def parse_geofences_json(s: str) -> List[Polygon]:
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


def segment_hits_nfz(
    n0: float,
    e0: float,
    n1: float,
    e1: float,
    nfz: Sequence[Polygon],
    *,
    min_step_m: float = 10.0,
    steps: int = 24,
) -> bool:
    segment_length_m = math.hypot(n1 - n0, e1 - e0)
    # FIX-GPP-G02: at least one sample every 5 m along the segment (min 24 samples)
    num_steps = max(24, int(segment_length_m / 5.0))
    if num_steps < 1:
        num_steps = 1
    for k in range(num_steps + 1):
        t = k / num_steps
        n = n0 + t * (n1 - n0)
        e = e0 + t * (e1 - e0)
        for poly in nfz:
            if point_in_polygon(n, e, poly):
                return True
    return False

