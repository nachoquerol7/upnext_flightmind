"""Shortest Dubins path (CSC / CCC) in NE plane; heading radians from North (CCW)."""

from __future__ import annotations

import math
from typing import Callable, List, Tuple

# Path types: (turn1, straight, turn2) with L=-1 R=+1 S=0
_PATHS = [
    ("LSL", -1, 0, -1),
    ("LSR", -1, 0, 1),
    ("RSL", 1, 0, -1),
    ("RSR", 1, 0, 1),
    ("RLR", 1, -1, 1),
    ("LRL", -1, 1, -1),
]


def _mod2pi(x: float) -> float:
    return (x + math.pi) % (2.0 * math.pi) - math.pi


def _polar(ax: float, ay: float) -> Tuple[float, float]:
    return math.hypot(ax, ay), math.atan2(ay, ax)


def _tau_omega(u: float, v: float, xi: float, eta: float, phi: float) -> Tuple[float, float, float]:
    delta = _mod2pi(u - v)
    a1 = 2.0 * math.sin(u) * (math.sin(delta + phi) - 2.0 * math.cos(u) * math.cos(phi))
    a1 += 2.0 * math.cos(delta) - 2.0 * math.cos(phi) + 1.0
    if abs(a1) < 1e-12:
        tau = 0.0
    else:
        tau = math.atan2(2.0 * math.cos(u) * (2.0 * math.cos(u) * math.cos(phi) - math.sin(delta + phi)) + 2.0 * math.sin(u) * math.cos(phi) - eta, a1)
    tau = _mod2pi(tau)
    omega = _mod2pi(tau - u + v - phi)
    return tau, omega, delta


def _csc_lengths(alpha: float, beta: float, d: float, f1: int, f2: int, f3: int) -> Tuple[float, float, float] | None:
    sa, ca = math.sin(alpha), math.cos(alpha)
    sb, cb = math.sin(beta), math.cos(beta)
    tmp = 2.0 + d * d - 2.0 * (ca * cb + sa * sb - d * (sa - sb))
    if tmp < -1e-9:
        return None
    tmp = max(0.0, tmp)
    p = math.sqrt(tmp)
    if f2 == 0:
        if f1 == -1 and f3 == -1:
            t = _mod2pi(-alpha + math.atan2(cb - ca, d + sa + sb))
            q = _mod2pi(beta - math.atan2(cb - ca, d + sa + sb))
            return t, p, q
        if f1 == 1 and f3 == 1:
            t = _mod2pi(alpha - math.atan2(ca - cb, d - sa - sb))
            q = _mod2pi(-beta + math.atan2(ca - cb, d - sa - sb))
            return t, p, q
        if f1 == -1 and f3 == 1:
            p2 = d * d + 2.0 + 2.0 * (cb * ca + sb * sa - d * (sb + sa))
            if p2 < -1e-9:
                return None
            p2 = max(0.0, p2)
            p = math.sqrt(p2)
            t = _mod2pi(-alpha + math.atan2(-cb - ca, d + sb - sa) - math.atan2(-2.0, p))
            q = _mod2pi(-beta + math.atan2(-cb - ca, d + sb - sa) - math.atan2(-2.0, p))
            return t, p, q
        if f1 == 1 and f3 == -1:
            p2 = d * d + 2.0 + 2.0 * (-cb * ca - sb * sa + d * (sb + sa))
            if p2 < -1e-9:
                return None
            p2 = max(0.0, p2)
            p = math.sqrt(p2)
            t = _mod2pi(alpha - math.atan2(cb + ca, d - sb + sa) + math.atan2(2.0, p))
            q = _mod2pi(beta - math.atan2(cb + ca, d - sb + sa) + math.atan2(2.0, p))
            return t, p, q
    return None


def _ccc_lengths(alpha: float, beta: float, d: float, f1: int, f2: int, f3: int) -> Tuple[float, float, float] | None:
    if f1 * f2 != -1 or f2 * f3 != -1:
        return None
    tmp = (6.0 - d * d + 2.0 * (math.cos(beta - alpha) + d * (math.sin(alpha) - math.sin(beta)))) / 8.0
    if abs(tmp) > 1.0 + 1e-6:
        return None
    tmp = max(-1.0, min(1.0, tmp))
    p = _mod2pi(2.0 * math.pi - math.acos(tmp))
    t = _mod2pi(alpha - math.atan2(math.cos(alpha) - math.cos(beta), d + math.sin(alpha) - math.sin(beta)) + p / 2.0 * f1)
    q = _mod2pi(alpha - beta - t + p * f2)
    return t, p, q


def dubins_length(n0: float, e0: float, h0: float, n1: float, e1: float, h1: float, rho: float) -> float:
    """Total path length (m); inf if infeasible."""
    if rho <= 1e-9:
        return float("inf")
    dx = (n1 - n0) / rho
    dy = (e1 - e0) / rho
    d, theta = _polar(dx, dy)
    alpha = _mod2pi(h0 - theta)
    beta = _mod2pi(h1 - theta)
    best = float("inf")
    for name, f1, f2, f3 in _PATHS:
        seg: Tuple[float, float, float] | None = None
        if f2 == 0:
            seg = _csc_lengths(alpha, beta, d, f1, f2, f3)
        else:
            seg = _ccc_lengths(alpha, beta, d, f1, f2, f3)
        if seg is None:
            continue
        t, p, q = seg
        L = abs(t) + abs(p) + abs(q)
        if L < best:
            best = L
    if best >= 1e8:
        return float("inf")
    return best * rho


def dubins_interpolate(
    n0: float, e0: float, h0: float, n1: float, e1: float, h1: float, rho: float
) -> Tuple[float, Callable[[float], Tuple[float, float, float]]]:
    """Return (length, s -> (n,e,heading))."""
    if rho <= 1e-9:
        return float("inf"), lambda s: (n0, e0, h0)

    dx = (n1 - n0) / rho
    dy = (e1 - e0) / rho
    d, theta = _polar(dx, dy)
    alpha = _mod2pi(h0 - theta)
    beta = _mod2pi(h1 - theta)
    best = float("inf")
    best_seg: Tuple[int, int, int, float, float, float] | None = None
    for _name, f1, f2, f3 in _PATHS:
        seg: Tuple[float, float, float] | None = None
        if f2 == 0:
            seg = _csc_lengths(alpha, beta, d, f1, f2, f3)
        else:
            seg = _ccc_lengths(alpha, beta, d, f1, f2, f3)
        if seg is None:
            continue
        t, p, q = seg
        L = abs(t) + abs(p) + abs(q)
        if L < best:
            best = L
            best_seg = (f1, f2, f3, t, p, q)
    if best_seg is None:
        return float("inf"), lambda s: (n0, e0, h0)
    f1, f2, f3, t, p, q = best_seg
    length_m = best * rho

    def integrate(s: float) -> Tuple[float, float, float]:
        """(x,y) in rho-normalized frame (turn radius = 1)."""
        s = max(0.0, min(s, length_m))
        u = s / rho
        x, y, psi = 0.0, 0.0, alpha

        def left(step: float) -> None:
            nonlocal x, y, psi
            if abs(step) < 1e-12:
                return
            x += math.sin(psi + step) - math.sin(psi)
            y += -math.cos(psi + step) + math.cos(psi)
            psi = _mod2pi(psi + step)

        def right(step: float) -> None:
            nonlocal x, y, psi
            if abs(step) < 1e-12:
                return
            x += -math.sin(psi - step) + math.sin(psi)
            y += math.cos(psi - step) - math.cos(psi)
            psi = _mod2pi(psi - step)

        def straight(step: float) -> None:
            nonlocal x, y
            x += step * math.cos(psi)
            y += step * math.sin(psi)

        rem = u
        segs = ((f1, abs(t), t), (f2, abs(p), p), (f3, abs(q), q))
        for kind, seg_len, seg_mag in segs:
            if rem <= 0:
                break
            take = min(rem, seg_len)
            if kind == -1:
                left(math.copysign(take, seg_mag))
            elif kind == 1:
                right(math.copysign(take, seg_mag))
            else:
                straight(math.copysign(take, seg_mag))
            rem -= take
        gn = n0 + rho * (x * math.cos(theta) - y * math.sin(theta))
        ge = e0 + rho * (x * math.sin(theta) + y * math.cos(theta))
        gh = _mod2pi(psi + theta)
        return gn, ge, gh

    return length_m, integrate
