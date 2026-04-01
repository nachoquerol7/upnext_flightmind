"""PolyCARP core geometry tests."""

from __future__ import annotations

import math

from polycarp_node.polycarp_core import evaluate_geofence_threat, point_in_polygon, time_to_polygon_entry


def test_punto_dentro_poligono() -> None:
    square = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))
    assert point_in_polygon(50.0, 50.0, square) is True


def test_punto_fuera_poligono() -> None:
    square = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))
    assert point_in_polygon(150.0, 50.0, square) is False


def test_poligono_vacio() -> None:
    imm, ttv = evaluate_geofence_threat(0.0, 0.0, 1.0, 0.0, [], imminent_horizon_s=30.0)
    assert imm is False
    assert ttv == float("inf")


def test_time_to_violation_outside_moving_in() -> None:
    square = ((200.0, 0.0), (300.0, 0.0), (300.0, 100.0), (200.0, 100.0))
    t = time_to_polygon_entry(0.0, 50.0, 50.0, 0.0, square, dt=0.05, max_time_s=20.0)
    assert math.isfinite(t)
    assert 3.5 < t < 5.5
