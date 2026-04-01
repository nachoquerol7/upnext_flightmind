"""Tabla simplificada: conflicto por rango/tau → RA vertical + cambio de rumbo."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


def _wrap_pi(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


@dataclass
class AcasConfig:
    tau_ca_s: float = 45.0
    dmod_ca_m: float = 1800.0
    z_sep_m: float = 120.0
    ra_climb_rate_mps: float = 3.0
    ra_heading_delta_deg: float = 30.0


@dataclass
class OwnshipState:
    n_m: float
    e_m: float
    z_ned_m: float
    vn_mps: float
    ve_mps: float
    vd_mps: float


@dataclass
class IntruderState:
    id: int
    n_m: float
    e_m: float
    z_ned_m: float
    vn_mps: float
    ve_mps: float
    vd_mps: float


@dataclass
class AcasDecision:
    ra_active: bool
    climb_rate_mps: float
    """Positive = climb (up, against NED +z)."""
    heading_delta_deg: float
    """Positive = turn right (clockwise from above)."""
    threat_class: str


def _horiz_hypot(a: float, b: float) -> float:
    return math.hypot(a, b)


def _tcpa_slant(
    rel_n: float,
    rel_e: float,
    rel_z: float,
    rvn: float,
    rve: float,
    rvd: float,
) -> float | None:
    """Closing time-of-flight to minimum range (s); None if not closing in range."""
    r = math.sqrt(rel_n * rel_n + rel_e * rel_e + rel_z * rel_z) + 1e-9
    rdot = (rel_n * rvn + rel_e * rve + rel_z * rvd) / r
    if rdot >= -1e-3:
        return None
    return -r / rdot


def _classify_geometry(own: OwnshipState, intr: IntruderState) -> str | None:
    rel_n = intr.n_m - own.n_m
    rel_e = intr.e_m - own.e_m
    v_own_h = (own.vn_mps, own.ve_mps)
    sp_o = _horiz_hypot(v_own_h[0], v_own_h[1])
    if sp_o < 2.0:
        return None
    uo = (v_own_h[0] / sp_o, v_own_h[1] / sp_o)
    in_front = rel_n * uo[0] + rel_e * uo[1] > 0.0

    own_trk = math.atan2(own.ve_mps, own.vn_mps)
    int_trk = math.atan2(intr.ve_mps, intr.vn_mps)
    dpsi = abs(_wrap_pi(own_trk - int_trk))
    sp_i = _horiz_hypot(intr.vn_mps, intr.ve_mps)

    if in_front and dpsi > math.radians(110.0):
        return "HEAD_ON"
    if in_front and dpsi < math.radians(70.0) and sp_o > sp_i + 8.0:
        return "OVERTAKE"
    return "GENERIC"


def _threat_with_intruder(own: OwnshipState, intr: IntruderState, cfg: AcasConfig) -> bool:
    rel_n = intr.n_m - own.n_m
    rel_e = intr.e_m - own.e_m
    rel_z = intr.z_ned_m - own.z_ned_m
    rvn = intr.vn_mps - own.vn_mps
    rve = intr.ve_mps - own.ve_mps
    rvd = intr.vd_mps - own.vd_mps

    hz = _horiz_hypot(rel_n, rel_e)
    if abs(rel_z) > cfg.z_sep_m and hz > cfg.dmod_ca_m * 0.5:
        return False

    tcpa = _tcpa_slant(rel_n, rel_e, rel_z, rvn, rve, rvd)
    if tcpa is not None and 0.0 < tcpa < cfg.tau_ca_s:
        return True
    # Proximidad horizontal: solo si nos acercamos en el plano NE (evita falso positivo en formación).
    if hz < cfg.dmod_ca_m and abs(rel_z) < cfg.z_sep_m * 1.5:
        relh_dot_rvh = rel_n * rvn + rel_e * rve
        if relh_dot_rvh < 0.0:
            return True
    return False


def compute_acas_decision(
    own: OwnshipState,
    intruders: Sequence[IntruderState],
    cfg: AcasConfig,
) -> AcasDecision:
    if not intruders:
        return AcasDecision(False, 0.0, 0.0, "")

    best_score = float("inf")
    picked: IntruderState | None = None

    for intr in intruders:
        if not _threat_with_intruder(own, intr, cfg):
            continue
        rel_n = intr.n_m - own.n_m
        rel_e = intr.e_m - own.e_m
        rel_z = intr.z_ned_m - own.z_ned_m
        rvn = intr.vn_mps - own.vn_mps
        rve = intr.ve_mps - own.ve_mps
        rvd = intr.vd_mps - own.vd_mps
        hz = _horiz_hypot(rel_n, rel_e)
        t = _tcpa_slant(rel_n, rel_e, rel_z, rvn, rve, rvd)
        score = float(t) if t is not None else hz
        if score < best_score:
            best_score = score
            picked = intr

    if picked is None:
        return AcasDecision(False, 0.0, 0.0, "")

    cls = _classify_geometry(own, picked) or "GENERIC"
    hd = cfg.ra_heading_delta_deg
    climb = cfg.ra_climb_rate_mps

    if cls == "HEAD_ON":
        return AcasDecision(True, climb, hd, cls)
    if cls == "OVERTAKE":
        return AcasDecision(True, -climb, 0.0, cls)
    return AcasDecision(True, climb, 0.5 * hd, cls)


def ownship_from_floats(data: Sequence[float]) -> OwnshipState | None:
    if len(data) < 6:
        return None
    return OwnshipState(
        n_m=float(data[0]),
        e_m=float(data[1]),
        z_ned_m=float(data[2]),
        vn_mps=float(data[3]),
        ve_mps=float(data[4]),
        vd_mps=float(data[5]),
    )
