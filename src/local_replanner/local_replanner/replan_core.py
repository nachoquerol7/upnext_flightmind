"""Cost model, FL adjustment, terrain margin scaling, vehicle-state helpers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from vehicle_model.model import TrajectorySegment, VehicleModel

# GPP FL convention: FL value such that altitude_ft = FL * 100 (feet), AMSL proxy.
FT_PER_FL_UNIT = 100.0
M_PER_FT = 0.3048


def fl_to_altitude_m(fl: float) -> float:
    return fl * FT_PER_FL_UNIT * M_PER_FT


def base_terrain_margin_m(fl_actual: float, terrain_max_m: float) -> float:
    return fl_to_altitude_m(fl_actual) - terrain_max_m


def margen_terreno_effective(fl_actual: float, terrain_max_m: float, quality_flag: float) -> float:
    """
    Altura AMSL proxy menos terreno; con peor calidad la reserva exigida sube → margen útil ↓.
    nominal: margen tal cual; degradado (≤0.8): margen/1.5; crítico (≤0.5): margen/2.0.
    """
    base = base_terrain_margin_m(fl_actual, terrain_max_m)
    if quality_flag > 0.8:
        m = base
    elif quality_flag > 0.5:
        m = base / 1.5
    else:
        m = base / 2.0
    return max(m, 1.0)


def replan_cost(
    margen_terreno: float,
    dist_nfz_m: float,
    desviacion_nominal_m: float,
    w1: float,
    w2: float,
    w3: float,
    *,
    eps: float = 1.0,
) -> float:
    mt = max(margen_terreno, eps)
    dn = max(dist_nfz_m, eps)
    return w1 * (1.0 / mt) + w2 * (1.0 / dn) + w3 * max(0.0, desviacion_nominal_m)


def delta_fl_for_quality(quality_flag: float) -> float:
    """Additional FL (100-ft units) when reacting to low quality."""
    if quality_flag < 0.5:
        return 5.0
    if quality_flag < 0.65:
        return 3.0
    return 1.0


def clamp_fl_delta_by_climb_rate(
    current_fl: float,
    proposed_fl: float,
    climb_rate_max_mps: float,
    dt_s: float,
) -> float:
    """Limit how much FL can rise in one cycle (vertical rate cap)."""
    max_dm = max(0.0, climb_rate_max_mps) * max(dt_s, 1e-3)
    max_dfl = max_dm / (FT_PER_FL_UNIT * M_PER_FT)
    target = max(proposed_fl, current_fl)
    return min(target, current_fl + max_dfl)


def vehicle_model_from_state_vector(data: List[float]) -> VehicleModel:
    """Build a static VehicleModel envelope from /vehicle_model/state (8 floats)."""
    p = parse_vehicle_state_vector(data)
    return VehicleModel(
        v_min_ms=p["v_min_ms"],
        v_max_ms=p["v_max_ms"],
        turn_radius_min_m=p["turn_radius_min_m"],
        climb_rate_max_ms=p["climb_rate_max_ms"],
        descent_rate_max_ms=p["descent_rate_max_ms"],
        glide_ratio=p["glide_ratio"],
        mtow_kg=750.0,
        fuel_burn_kgh=50.0,
        fuel_mass_initial_kg=100.0,
        v_min_reserve_gain_ms=0.0,
    )


def parse_vehicle_state_vector(data: List[float]) -> Dict[str, float]:
    """Unpack /vehicle_model/state (8 floats)."""
    if len(data) < 8:
        raise ValueError("vehicle_model state expects 8 fields")
    return {
        "v_min_ms": float(data[0]),
        "v_max_ms": float(data[1]),
        "turn_radius_min_m": float(data[2]),
        "climb_rate_max_ms": float(data[3]),
        "descent_rate_max_ms": float(data[4]),
        "glide_ratio": float(data[5]),
        "mass_kg": float(data[6]),
        "fuel_remaining_kg": float(data[7]),
    }


def parse_emergency_landing_json(s: str) -> Dict[str, Any]:
    if not s or not s.strip():
        return {}
    return json.loads(s)


def emergency_waypoint_ne(
    d: Mapping[str, Any],
    own_n: float,
    own_e: float,
    *,
    ref_lat_deg: float = 40.0,
    ref_lon_deg: float = -3.0,
    ref_n_m: float = 0.0,
    ref_e_m: float = 0.0,
) -> Tuple[float, float]:
    """Prefer explicit n_m/e_m in JSON; else flat-earth from lat/lon vs reference."""
    if d.get("n_m") is not None and d.get("e_m") is not None:
        return float(d["n_m"]), float(d["e_m"])
    if "lat" not in d or "lon" not in d:
        return own_n, own_e
    lat, lon = float(d["lat"]), float(d["lon"])
    dn = (lat - ref_lat_deg) * 111320.0
    de = (lon - ref_lon_deg) * 111320.0 * math.cos(math.radians(ref_lat_deg))
    return ref_n_m + dn, ref_e_m + de


def daidalus_advisory_feasible(vehicle: VehicleModel, ra_gs: float, ra_vs_mps: float) -> bool:
    seg = TrajectorySegment(
        speed_mps=ra_gs,
        climb_rate_mps=ra_vs_mps,
        turn_radius_m=float("inf"),
    )
    return vehicle.is_feasible([seg])


def cross_track_deviation_m(
    n: float,
    e: float,
    path_ne: List[Tuple[float, float]],
) -> float:
    """Min distance from (n,e) to polyline path in NE plane."""
    if len(path_ne) < 2:
        return 0.0
    best = float("inf")
    for i in range(len(path_ne) - 1):
        n0, e0 = path_ne[i]
        n1, e1 = path_ne[i + 1]
        dn, de = n1 - n0, e1 - e0
        L2 = dn * dn + de * de
        if L2 < 1e-12:
            d = math.hypot(n - n0, e - e0)
        else:
            t = max(0.0, min(1.0, ((n - n0) * dn + (e - e0) * de) / L2))
            pn, pe = n0 + t * dn, e0 + t * de
            d = math.hypot(n - pn, e - pe)
        best = min(best, d)
    return best
