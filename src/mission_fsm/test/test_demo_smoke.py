"""Smoke críticos para demo (8 Apr 2026) — TC-DEMO-001..003."""

from __future__ import annotations

import json
import math
import time
from types import SimpleNamespace

import pytest

from gpp.rrt_star import RRTStarPlanner


def _dwell_spin(h: SimpleNamespace, iterations: int) -> None:
    """Avanza reloj + ejecutor (misma cadencia que M2 timeouts)."""
    for _ in range(iterations):
        time.sleep(0.045)
        for _ in range(12):
            h.ex.spin_once(timeout_sec=0.02)


def _circle_polygon(cn: float, ce: float, disk_radius_m: float, sides: int) -> tuple[tuple[float, float], ...]:
    rv = disk_radius_m / math.cos(math.pi / max(sides, 3))
    return tuple(
        (cn + rv * math.cos(2.0 * math.pi * i / sides), ce + rv * math.sin(2.0 * math.pi * i / sides))
        for i in range(sides)
    )


def _min_dist_to_point(path: list[tuple[float, float, float]], pn: float, pe: float) -> float:
    return min(math.hypot(s[0] - pn, s[1] - pe) for s in path)


@pytest.mark.demo
@pytest.mark.slow
@pytest.mark.tight_dwell
@pytest.mark.timeout(60)
def test_tc_demo_001_takeoff_dwell_timeout_to_abort(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-DEMO-001: morada en TAKEOFF sin señal de progreso → timeout → ABORT (pérdida de señal / no complete)."""
    h = mission_fsm_sil_harness
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    # Umbral: elapsed_wall >= max_duration_sec (5.0); cada iter aporta ~0.045 s de sleep → >=112 iter.
    _dwell_spin(h, 115)
    assert h.fsm._fsm.state != "TAKEOFF"  # noqa: SLF001


@pytest.mark.demo
@pytest.mark.slow
@pytest.mark.timeout(45)
def test_tc_demo_002_quality_drop_enters_event(mission_fsm_sil_harness: SimpleNamespace) -> None:
    """TC-DEMO-002: degradación de navegación (quality bajo) → EVENT.

    En integración, FDIR/watchdog puede empujar `quality_flag` abajo; en SIL se inyecta
    el mismo átomo que consume el FSM (`quality_degraded`).
    """
    h = mission_fsm_sil_harness
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    h.inj.inject("takeoff_complete", True)
    assert h.wait_mode("CRUISE")
    h.inj.inject("quality_flag", 0.1)
    assert h.wait_mode("EVENT")


@pytest.mark.demo
@pytest.mark.timeout(30)
def test_tc_demo_003_gpp_avoids_nfz_min_dist() -> None:
    """TC-DEMO-003: GPP (RRT*) evita NFZ y la ruta mantiene separación > 50 m del eje del obstáculo."""
    turn_r = 75.0
    planner = RRTStarPlanner(turn_r, max_iter=1200, seed=42)
    start = (0.0, 0.0, 0.0)
    goal = (500.0, 0.0, 0.0)
    cn, ce = 250.0, 0.0
    disk_r = 80.0
    poly = _circle_polygon(cn, ce, disk_r, 64)
    bounds = (-100.0, 600.0, -200.0, 200.0)
    nfz_json = json.dumps({"polygons": [[list(p) for p in poly]]})
    path = planner.plan_if_needed(start, goal, [poly], bounds, [500.0, 0.0, 0.0], nfz_json)
    assert len(path) >= 2, "expected a feasible path around NFZ"
    min_d = _min_dist_to_point(path, cn, ce)
    assert min_d > 50.0, f"min horizontal dist to NFZ center {min_d:.1f}m, expected > 50m"
