"""Dubins CSC/CCC in NE + altitude profile; checks against VehicleModel."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from gpp.dubins import dubins_interpolate
from vehicle_model.model import TrajectorySegment, VehicleModel


def _mod2pi(x: float) -> float:
    return (x + math.pi) % (2.0 * math.pi) - math.pi


def vehicle_model_from_state_vector(data: Sequence[float]) -> VehicleModel:
    """Same 8-float layout as `/vehicle_model/state` (vehicle_model_node)."""
    if len(data) < 8:
        raise ValueError("vehicle_model state expects 8 fields")
    return VehicleModel(
        v_min_ms=float(data[0]),
        v_max_ms=float(data[1]),
        turn_radius_min_m=float(data[2]),
        climb_rate_max_ms=float(data[3]),
        descent_rate_max_ms=float(data[4]),
        glide_ratio=float(data[5]),
        mtow_kg=750.0,
        fuel_burn_kgh=50.0,
        fuel_mass_initial_kg=100.0,
        v_min_reserve_gain_ms=0.0,
    )


def path_sample_density_pts_per_m(alert_level: int) -> float:
    """Higher DAIDALUS alert → denser sampling along Dubins length."""
    return 1.0 if int(alert_level) >= 1 else 0.2


def num_samples_for_length(length_m: float, alert_level: int) -> int:
    d = path_sample_density_pts_per_m(alert_level)
    return max(3, int(max(0.0, length_m) * d) + 1)


def cruise_speed_for_vm(vm: VehicleModel, override: float | None) -> float:
    if override is not None and math.isfinite(override):
        return float(override)
    return 0.5 * (vm.v_min_ms + vm.v_max_ms)


def build_setpoints_leg(
    n0: float,
    e0: float,
    z0: float,
    h0: float,
    n1: float,
    e1: float,
    z1: float,
    h1: float,
    vm: VehicleModel,
    *,
    alert_level: int = 0,
    cruise_speed_ms: float | None = None,
) -> Tuple[bool, List[List[float]], str]:
    """
    One Dubins 3D leg: horizontal CSC/CCC with rho = turn_radius_min_m;
    z interpolated linearly in arc length. Each setpoint: [n,e,z,heading,speed].
    """
    rho = vm.turn_radius_min_m
    L, fn = dubins_interpolate(n0, e0, h0, n1, e1, h1, rho)
    if not math.isfinite(L) or L <= 1e-6 or L > 1e8:
        return False, [], "dubins_horizontal_infeasible"

    v_cruise = cruise_speed_for_vm(vm, cruise_speed_ms)
    n_s = num_samples_for_length(L, alert_level)
    pts: List[List[float]] = []
    for i in range(n_s):
        s = L * i / max(n_s - 1, 1)
        gn, ge, gh = fn(s)
        t = s / L if L > 1e-9 else 0.0
        z = z0 + (z1 - z0) * t
        pts.append([gn, ge, z, gh, v_cruise])

    ok, reason = verify_setpoints_against_vm(pts, vm)
    if not ok:
        return False, pts, reason
    return True, pts, ""


def setpoints_to_trajectory_segments(setpoints: Sequence[Sequence[float]]) -> List[TrajectorySegment]:
    """Polyline segments: horizontal speed v, climb from Δz/Δt, turn radius from Δheading/Δs."""
    segs: List[TrajectorySegment] = []
    if len(setpoints) < 2:
        return segs
    for i in range(len(setpoints) - 1):
        a = setpoints[i]
        b = setpoints[i + 1]
        n0, e0, z0, h0, v0 = float(a[0]), float(a[1]), float(a[2]), float(a[3]), float(a[4])
        n1, e1, z1 = float(b[0]), float(b[1]), float(b[2])
        v1 = float(b[4]) if len(b) > 4 else v0
        v = 0.5 * (v0 + v1)
        ds = math.hypot(n1 - n0, e1 - e0)
        dz = z1 - z0
        if ds < 1e-4:
            dt = abs(dz) / max(v, 1e-6)
            if dt < 1e-6:
                continue
            climb = dz / dt
            segs.append(TrajectorySegment(speed_mps=v, climb_rate_mps=climb, turn_radius_m=float("inf")))
            continue
        dt = ds / max(v, 1e-6)
        climb = dz / dt
        dh = _mod2pi(float(b[3]) - h0)
        half = 0.5 * abs(dh)
        if half < 1e-6:
            r_turn = float("inf")
        else:
            # Chord length ds and heading change along a circular arc: R = ds / (2*sin(Δψ/2)).
            r_turn = ds / (2.0 * math.sin(min(half, math.pi * 0.5 - 1e-6)))
        segs.append(TrajectorySegment(speed_mps=v, climb_rate_mps=climb, turn_radius_m=r_turn))
    return segs


def verify_setpoints_against_vm(setpoints: Sequence[Sequence[float]], vm: VehicleModel) -> Tuple[bool, str]:
    """Discretised checks; horizontal curvature via chord: R = ds/|Δψ| ≥ R_min."""
    segs = setpoints_to_trajectory_segments(setpoints)
    if not segs:
        return False, "empty_trajectory"
    if not vm.is_feasible(segs):
        for seg in segs:
            if seg.speed_mps < vm.v_min_ms - 1e-9:
                return False, "below_v_min"
            if seg.speed_mps > vm.v_max_ms + 1e-9:
                return False, "above_v_max"
            if seg.climb_rate_mps > vm.climb_rate_max_ms + 1e-9:
                return False, "climb_rate_exceeded"
            if seg.climb_rate_mps < -vm.descent_rate_max_ms - 1e-9:
                return False, "descent_rate_exceeded"
            if seg.turn_radius_m < vm.turn_radius_min_m - 1e-9:
                return False, "turn_radius_violation"
        return False, "vehicle_model_infeasible"
    return True, ""


def build_full_path_setpoints(
    waypoints_nezh: Sequence[Tuple[float, float, float, float]],
    vm: VehicleModel,
    *,
    alert_level: int = 0,
    cruise_speed_ms: float | None = None,
) -> Tuple[bool, List[List[float]], str]:
    """Chain Dubins legs between consecutive (n,e,z,h) waypoints."""
    if len(waypoints_nezh) < 2:
        return False, [], "insufficient_waypoints"
    out: List[List[float]] = []
    for i in range(len(waypoints_nezh) - 1):
        w0 = waypoints_nezh[i]
        w1 = waypoints_nezh[i + 1]
        ok, leg, reason = build_setpoints_leg(
            w0[0], w0[1], w0[2], w0[3], w1[0], w1[1], w1[2], w1[3], vm,
            alert_level=alert_level,
            cruise_speed_ms=cruise_speed_ms,
        )
        if not ok:
            return False, out + leg, reason
        if out and leg:
            leg = leg[1:]
        out.extend(leg)
    return True, out, ""
