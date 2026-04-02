#!/usr/bin/env python3
"""Standalone demo T1: GPP evita NFZ cilíndrica (polígono regular) vía gpp_node en proceso.

Ejecutar desde el workspace (ver README interno del paquete gpp).
"""
from __future__ import annotations

import json
import math
import sys
import time

import rclpy
from nav_msgs.msg import Path
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from std_msgs.msg import Float64, Float64MultiArray, String

from gpp.gpp_node import GppNode

# Escenario: línea recta conceptual (0,0)→(500,0) a altitud de vuelo fija; el nodo planifica en NE.
START_N, START_E = 0.0, 0.0
GOAL_N, GOAL_E = 500.0, 0.0
GOAL_HEADING_RAD = 0.0
NFZ_CENTER_N, NFZ_CENTER_E = 250.0, 0.0
NFZ_RADIUS_M = 80.0
NFZ_SIDES = 64
MAX_PLAN_S = 2.0


def _circle_polygon_circumscribed(cn: float, ce: float, disk_radius_m: float, sides: int) -> tuple[tuple[float, float], ...]:
    """Polígono convexo que contiene el disco horizontal de radio disk_radius_m (apotema = radio)."""
    rv = disk_radius_m / math.cos(math.pi / max(sides, 3))
    return tuple(
        (cn + rv * math.cos(2.0 * math.pi * i / sides), ce + rv * math.sin(2.0 * math.pi * i / sides))
        for i in range(sides)
    )


def _min_dist_to_nfz_center(path: Path, cn: float, ce: float) -> float:
    m = float("inf")
    for ps in path.poses:
        n = float(ps.pose.position.x)
        e = float(ps.pose.position.y)
        d = math.hypot(n - cn, e - ce)
        m = min(m, d)
    return m


def main() -> int:
    if not rclpy.ok():
        rclpy.init()

    # Radio de giro menor que el default (600 m) para poder orillar la NFZ en escenario estrecho.
    gpp = GppNode(parameter_overrides=[Parameter("turn_radius_min_m", value=75.0)])
    spy = rclpy.create_node("demo_t1_spy")
    ex = SingleThreadedExecutor()
    ex.add_node(gpp)
    ex.add_node(spy)

    last_path: list[Path | None] = [None]
    status: list[str | None] = [None]

    def _on_path(msg: Path) -> None:
        last_path[0] = msg

    def _on_status(msg: String) -> None:
        status[0] = msg.data

    spy.create_subscription(Path, "/gpp/global_path", _on_path, 10)
    spy.create_subscription(String, "/gpp/status", _on_status, 10)

    pub_terrain = spy.create_publisher(Float64, "/gpp/terrain_max_m", 10)
    pub_ceiling = spy.create_publisher(Float64, "/gpp/ceiling_m", 10)
    pub_quality = spy.create_publisher(Float64, "/nav/quality_flag", 10)
    pub_goal = spy.create_publisher(Float64MultiArray, "/gpp/goal", 10)
    pub_geo = spy.create_publisher(String, "/airspace/geofences", 10)
    pub_own = spy.create_publisher(Float64MultiArray, "/ownship/state", 10)
    pub_to = spy.create_publisher(Float64MultiArray, "/gpp/takeoff_state", 10)

    def spin_until(pred, timeout_sec: float) -> bool:
        end = time.perf_counter() + timeout_sec
        while time.perf_counter() < end:
            ex.spin_once(timeout_sec=0.02)
            if pred():
                return True
        return False

    def spin_for(seconds: float) -> None:
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            ex.spin_once(timeout_sec=0.02)

    try:
        pub_terrain.publish(Float64(data=1000.0))
        pub_ceiling.publish(Float64(data=8000.0))
        pub_quality.publish(Float64(data=0.9))
        # n, e, ?, vn, ve, ? — rumbo hacia +N
        pub_own.publish(
            Float64MultiArray(data=[START_N, START_E, 0.0, 20.0, 0.0, 0.0])
        )
        pub_to.publish(Float64MultiArray(data=[0.0, 0.0, 0.0, 0.0, 0.0]))

        if not spin_until(lambda: status[0] == "OK", 3.0):
            print("[T1] GPP NFZ Avoidance")
            print("  ✗ GPP status never reached OK (terrain/ceiling/quality).")
            print("  RESULT: FAIL")
            return 1

        wall = _circle_polygon_circumscribed(NFZ_CENTER_N, NFZ_CENTER_E, NFZ_RADIUS_M, NFZ_SIDES)
        # Un polígono = lista de vértices [n,e]; no confundir con [list(v) for v in wall] (64 polígonos inválidos).
        geo_json = json.dumps({"polygons": [[list(vertex) for vertex in wall]]})
        # Misma garantía que un mensaje ROS recibido (evita carrera DDS en demo standalone).
        gpp._on_geo(String(data=geo_json))
        if not gpp._nfz_polys:
            print("[T1] GPP NFZ Avoidance")
            print("  ✗ NFZ no cargada tras _on_geo.")
            print("  RESULT: FAIL")
            return 1
        pub_geo.publish(String(data=geo_json))
        spin_for(0.15)

        last_path[0] = None
        t0 = time.perf_counter()
        pub_goal.publish(Float64MultiArray(data=[GOAL_N, GOAL_E, GOAL_HEADING_RAD]))

        if not spin_until(
            lambda: last_path[0] is not None and len(last_path[0].poses) >= 2,
            4.0,
        ):
            t1 = time.perf_counter()
            plan_s = t1 - t0
            print("[T1] GPP NFZ Avoidance")
            print("  ✗ Route clear of NFZ (min_dist=0.0m)")
            print(f"  ✗ Planning time: {plan_s:.2f}s")
            print("  RESULT: FAIL")
            print("    — Timeout esperando /gpp/global_path con >=2 poses.")
            return 1
        t1 = time.perf_counter()
        plan_s = t1 - t0

        p = last_path[0]
        ok = True
        reasons: list[str] = []

        if p is None or len(p.poses) < 2:
            ok = False
            reasons.append("No se recibió path válido (>=2 poses).")
            min_d = 0.0
        else:
            min_d = _min_dist_to_nfz_center(p, NFZ_CENTER_N, NFZ_CENTER_E)
            if min_d < NFZ_RADIUS_M - 0.5:
                ok = False
                reasons.append(
                    f"Waypoint demasiado cerca del eje NFZ: min_dist={min_d:.2f}m (< {NFZ_RADIUS_M}m)."
                )
            if plan_s >= MAX_PLAN_S:
                ok = False
                reasons.append(f"Planificación lenta: {plan_s:.2f}s (>= {MAX_PLAN_S}s).")

        print("[T1] GPP NFZ Avoidance")
        if p is not None and len(p.poses) >= 2 and min_d >= NFZ_RADIUS_M - 0.5:
            print(f"  ✓ Route clear of NFZ (min_dist={min_d:.1f}m)")
        else:
            print(f"  ✗ Route clear of NFZ (min_dist={min_d:.1f}m)")
        if plan_s < MAX_PLAN_S:
            print(f"  ✓ Planning time: {plan_s:.2f}s")
        else:
            print(f"  ✗ Planning time: {plan_s:.2f}s")
        if ok:
            print("  RESULT: PASS")
        else:
            print("  RESULT: FAIL")
            for r in reasons:
                print(f"    — {r}")
            return 1
        return 0
    finally:
        ex.remove_node(spy)
        ex.remove_node(gpp)
        spy.destroy_node()
        gpp.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
