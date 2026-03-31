"""Carga GeoJSON FeatureCollection con polígonos (lon, lat)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AirspaceZone:
    zone_id: str
    name: str
    floor_m: float
    ceiling_m: float
    # anillo exterior GeoJSON: lista [lon, lat]
    ring_ll: List[List[float]]


def load_zones(path: str | Path) -> List[AirspaceZone]:
    p = Path(path)
    with p.open(encoding='utf-8') as f:
        data: Dict[str, Any] = json.load(f)

    if data.get('type') != 'FeatureCollection':
        raise ValueError('Se espera FeatureCollection')

    zones: List[AirspaceZone] = []
    for feat in data.get('features', []):
        geom = feat.get('geometry') or {}
        props = feat.get('properties') or {}
        if geom.get('type') != 'Polygon':
            continue
        coords = geom.get('coordinates') or []
        if not coords:
            continue
        ring = coords[0]  # exterior ring
        zid = str(props.get('id', f'zone_{len(zones)}'))
        name = str(props.get('name', zid))
        floor_m = float(props.get('floor_m', 0.0))
        ceiling_m = float(props.get('ceiling_m', 9999.0))
        zones.append(
            AirspaceZone(
                zone_id=zid,
                name=name,
                floor_m=floor_m,
                ceiling_m=ceiling_m,
                ring_ll=[list(pt) for pt in ring],
            )
        )
    return zones


def centroid_deg(zones: List[AirspaceZone]) -> tuple[float, float]:
    """Centro aproximado (media de vértices de todas las zonas)."""
    if not zones:
        return 40.0, -3.7
    lats: List[float] = []
    lons: List[float] = []
    for z in zones:
        for pt in z.ring_ll:
            lons.append(float(pt[0]))
            lats.append(float(pt[1]))
    return sum(lats) / len(lats), sum(lons) / len(lons)
