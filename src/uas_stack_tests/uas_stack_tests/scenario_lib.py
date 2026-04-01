"""Métricas DAA/ACAS para escenarios SIL: CSV en results/."""

from __future__ import annotations

import csv
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import rclpy
from flightmind_msgs.msg import TrafficIntruder, TrafficReport
from rclpy.node import Node
from std_msgs.msg import Bool, Float64MultiArray, String


@dataclass
class OwnshipKinematic:
    n: float
    e: float
    z: float
    vn: float
    ve: float
    vd: float


def estimate_miss_distance_m(own: OwnshipKinematic, intr: OwnshipKinematic, horizon_s: float) -> float:
    """Distancia mínima en horizonte con velocidades constantes (slant, m)."""
    best = float("inf")
    rel_n = intr.n - own.n
    rel_e = intr.e - own.e
    rel_z = intr.z - own.z
    rvn = intr.vn - own.vn
    rve = intr.ve - own.ve
    rvd = intr.vd - own.vd
    steps = int(max(2, horizon_s / 0.1))
    for i in range(steps + 1):
        t = horizon_s * i / steps
        dn = rel_n + rvn * t
        de = rel_e + rve * t
        dz = rel_z + rvd * t
        d = math.sqrt(dn * dn + de * de + dz * dz)
        if d < best:
            best = d
    return best


def ra_type_label(climb_mps: float, hdg_deg: float, ra_active: bool) -> str:
    if not ra_active:
        return "NONE"
    if climb_mps > 0.5:
        return "CLIMB"
    if climb_mps < -0.5:
        return "DESCEND"
    if abs(hdg_deg) > 1.0:
        return "TURN"
    return "MIXED"


def default_results_dir() -> Path:
    env = os.environ.get("UAS_STACK_RESULTS_DIR", "").strip()
    out = Path(env) if env else Path.cwd() / "results"
    out.mkdir(parents=True, exist_ok=True)
    return out


class ScenarioRunner(Node):
    def __init__(
        self,
        *,
        scenario_name: str,
        ownship_fn: Callable[[float], OwnshipKinematic],
        intruder_fn: Callable[[float], TrafficIntruder],
        duration_s: float = 12.0,
        results_dir: Optional[Path] = None,
        geofence_json_fn: Optional[Callable[[float], str]] = None,
    ) -> None:
        super().__init__(f"scenario_{scenario_name}")
        self._name = scenario_name
        self._own_fn = ownship_fn
        self._intr_fn = intruder_fn
        self._duration = duration_s
        self._t0 = time.monotonic()
        self._results = results_dir or default_results_dir()
        self._geo_fn = geofence_json_fn

        self._t_alert: Optional[float] = None
        self._bands: List[float] = [0.0, 1e9, 1e9]
        self._ra_active = False
        self._ra_vec = [0.0, 0.0]
        self._geofence_imm = False

        self._pub_own = self.create_publisher(Float64MultiArray, "/ownship/state", 10)
        self._pub_traffic = self.create_publisher(TrafficReport, "/traffic/intruders", 10)
        self._pub_geo = self.create_publisher(String, "/airspace/geofences", 10)

        self.create_subscription(Float64MultiArray, "/daidalus/bands_summary", self._on_bands, 10)
        self.create_subscription(Bool, "/acas/ra_active", self._on_ra, 10)
        self.create_subscription(Float64MultiArray, "/acas/resolution_advisory", self._on_ra_vec, 10)
        self.create_subscription(Bool, "/polycarp/violation_imminent", self._on_geo, 10)

        self._timer = self.create_timer(0.05, self._tick_pub)
        self._finished = False

    def _on_bands(self, msg: Float64MultiArray) -> None:
        if len(msg.data) >= 3:
            self._bands = [float(msg.data[0]), float(msg.data[1]), float(msg.data[2])]
            if self._t_alert is None and self._bands[0] >= 1.0:
                self._t_alert = time.monotonic() - self._t0

    def _on_ra(self, msg: Bool) -> None:
        self._ra_active = bool(msg.data)

    def _on_ra_vec(self, msg: Float64MultiArray) -> None:
        if len(msg.data) >= 2:
            self._ra_vec = [float(msg.data[0]), float(msg.data[1])]

    def _on_geo(self, msg: Bool) -> None:
        self._geofence_imm = bool(msg.data)

    def _tick_pub(self) -> None:
        now = time.monotonic() - self._t0
        if now > self._duration:
            if not self._finished:
                self._write_csv(now)
                self._finished = True
            return

        o = self._own_fn(now)
        om = Float64MultiArray()
        om.data = [o.n, o.e, o.z, o.vn, o.ve, o.vd]
        self._pub_own.publish(om)

        tr = TrafficReport()
        intr = self._intr_fn(now)
        tr.intruders = [intr]
        self._pub_traffic.publish(tr)
        if self._geo_fn is not None:
            self._pub_geo.publish(String(data=self._geo_fn(now)))

    def _write_csv(self, elapsed: float) -> None:
        o = self._own_fn(0.0)
        intr_msg = self._intr_fn(0.0)
        ik = OwnshipKinematic(
            intr_msg.n_m, intr_msg.e_m, intr_msg.z_ned_m,
            intr_msg.vn_mps, intr_msg.ve_mps, intr_msg.vd_mps,
        )
        miss = estimate_miss_distance_m(o, ik, min(120.0, self._duration * 3.0))
        ra_t = ra_type_label(self._ra_vec[0], self._ra_vec[1], self._ra_active)
        path = self._results / f"{self._name}.csv"
        row = {
            "scenario": self._name,
            "t_alert_s": "" if self._t_alert is None else f"{self._t_alert:.4f}",
            "miss_distance_m": f"{miss:.2f}",
            "ra_type": ra_t,
            "num_conflict_final": f"{self._bands[0]:.1f}",
            "minH_final": f"{self._bands[1]:.2f}",
            "minV_final": f"{self._bands[2]:.2f}",
            "geofence_imminent": str(self._geofence_imm),
            "elapsed_s": f"{elapsed:.2f}",
        }
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            w.writeheader()
            w.writerow(row)
        self.get_logger().info(f"escenario {self._name} → {path}")


def run_scenario_node(
    *,
    scenario_name: str,
    ownship_fn: Callable[[float], OwnshipKinematic],
    intruder_fn: Callable[[float], TrafficIntruder],
    duration_s: float = 12.0,
    results_dir: Optional[Path] = None,
    geofence_json_fn: Optional[Callable[[float], str]] = None,
) -> None:
    rclpy.init()
    node = ScenarioRunner(
        scenario_name=scenario_name,
        ownship_fn=ownship_fn,
        intruder_fn=intruder_fn,
        duration_s=duration_s,
        results_dir=results_dir,
        geofence_json_fn=geofence_json_fn,
    )
    try:
        while rclpy.ok() and not node._finished:
            rclpy.spin_once(node, timeout_sec=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
