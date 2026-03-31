"""Proyección local equirectangular simple (áreas pequeñas) y punto en polígono."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

# Radio medio WGS84 (m)
_EARTH_R = 6371009.0


def ll_to_xy_m(
    lat_deg: float,
    lon_deg: float,
    origin_lat_deg: float,
    origin_lon_deg: float,
) -> Tuple[float, float]:
    """Retorna (x_east_m, y_north_m) respecto al origen."""
    lat0 = math.radians(origin_lat_deg)
    dlat = math.radians(lat_deg - origin_lat_deg)
    dlon = math.radians(lon_deg - origin_lon_deg)
    y_north = dlat * _EARTH_R
    x_east = dlon * _EARTH_R * math.cos(lat0)
    return x_east, y_north


def ring_ll_to_xy(
    ring_ll: Sequence[Sequence[float]],
    origin_lat_deg: float,
    origin_lon_deg: float,
) -> List[Tuple[float, float]]:
    out: List[Tuple[float, float]] = []
    for pt in ring_ll:
        lon, lat = float(pt[0]), float(pt[1])
        x, y = ll_to_xy_m(lat, lon, origin_lat_deg, origin_lon_deg)
        out.append((x, y))
    return out


def point_in_polygon_xy(x: float, y: float, poly: Sequence[Tuple[float, float]]) -> bool:
    """Ray casting; poly cerrado (primer punto = último o no)."""
    n = len(poly)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def point_in_polygon_ll(
    lat_deg: float,
    lon_deg: float,
    ring_ll: Sequence[Sequence[float]],
    origin_lat_deg: float,
    origin_lon_deg: float,
) -> bool:
    """Mismo origen que la visualización; anillo GeoJSON (lon, lat)."""
    qx, qy = ll_to_xy_m(lat_deg, lon_deg, origin_lat_deg, origin_lon_deg)
    poly_xy = ring_ll_to_xy(ring_ll, origin_lat_deg, origin_lon_deg)
    if len(poly_xy) >= 2 and poly_xy[0] == poly_xy[-1]:
        poly_xy = poly_xy[:-1]
    return point_in_polygon_xy(qx, qy, poly_xy)
