#!/usr/bin/env python3
"""
Dashboard rápido ICAROUS/DAIDALUS:
- Mapa EN con geofence + ownship/intruder + trails
- Series de bandas (numConflict, minH, minV)
- Panel de eventos (enter/exit conflicto)

Uso:
  source /opt/ros/jazzy/setup.bash
  source ~/upnext_uas_ws/install/setup.bash
  python3 ~/upnext_uas_ws/scripts/daa_bands_dashboard.py
"""

from __future__ import annotations

import math
import time
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
import rclpy
from px4_msgs.msg import VehicleGlobalPosition
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class DaaDashboard(Node):
    def __init__(self) -> None:
        super().__init__("daa_bands_dashboard")
        self.sub_bands = self.create_subscription(
            Float64MultiArray,
            "/upnext_daa/daa_traffic_monitor/daa/bands_summary",
            self.on_bands,
            10,
        )
        self.sub_gpos = self.create_subscription(
            VehicleGlobalPosition,
            "/fmu/out/vehicle_global_position",
            self.on_gpos,
            10,
        )

        self.history_t = deque(maxlen=300)
        self.history_conflict = deque(maxlen=300)
        self.history_min_h = deque(maxlen=300)
        self.history_min_v = deque(maxlen=300)
        self.own_trail = deque(maxlen=600)
        self.intr_trail = deque(maxlen=600)
        self.events = deque(maxlen=8)

        self.ref_lat = None
        self.ref_lon = None
        self.own_x = 0.0
        self.own_y = 0.0
        self.own_alt = 0.0

        # Intruder sintético (igual que el demo actual por defecto)
        self.intr_n = 50.0
        self.intr_e = 0.0
        self.intr_vn = 0.0
        self.intr_ve = -4.0
        self.t0 = time.time()

        self.last_bands = np.array([0.0, 0.0, 0.0, -1.0, -1.0, -1.0], dtype=float)
        self.was_conflict = False

    def on_bands(self, msg: Float64MultiArray) -> None:
        vals = np.array(list(msg.data), dtype=float)
        if vals.size < 3:
            return
        if vals.size < 6:
            vals = np.pad(vals, (0, 6 - vals.size), constant_values=-1.0)
        self.last_bands = vals
        now = time.time() - self.t0
        self.history_t.append(now)
        self.history_conflict.append(vals[0])
        self.history_min_h.append(vals[1])
        self.history_min_v.append(vals[2])

        is_conflict = vals[0] >= 1.0
        if is_conflict and not self.was_conflict:
            self.events.appendleft(f"T+{now:5.1f}s  CONFLICT ENTER  (minH={vals[1]:.1f}m)")
        elif (not is_conflict) and self.was_conflict:
            self.events.appendleft(f"T+{now:5.1f}s  CONFLICT CLEAR")
        self.was_conflict = is_conflict

    def on_gpos(self, msg: VehicleGlobalPosition) -> None:
        lat = float(msg.lat)
        lon = float(msg.lon)
        alt = float(msg.alt)
        if self.ref_lat is None:
            self.ref_lat = lat
            self.ref_lon = lon
        lat_rad = math.radians(self.ref_lat)
        dlat = (lat - self.ref_lat) * math.pi / 180.0
        dlon = (lon - self.ref_lon) * math.pi / 180.0
        r = 6378137.0
        self.own_x = dlon * math.cos(lat_rad) * r
        self.own_y = dlat * r
        self.own_alt = alt
        self.own_trail.append((self.own_x, self.own_y))

    def intruder_xy(self) -> tuple[float, float]:
        dt = time.time() - self.t0
        return self.intr_e + self.intr_ve * dt, self.intr_n + self.intr_vn * dt


def main() -> int:
    rclpy.init()
    node = DaaDashboard()

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(13, 8))
    gs = fig.add_gridspec(2, 3, width_ratios=[2.2, 1.0, 1.0])
    ax_map = fig.add_subplot(gs[:, 0])
    ax_conf = fig.add_subplot(gs[0, 1])
    ax_minh = fig.add_subplot(gs[0, 2])
    ax_minv = fig.add_subplot(gs[1, 1])
    ax_evt = fig.add_subplot(gs[1, 2])

    fig.suptitle("ICAROUS / DAIDALUS Dashboard", fontsize=14)

    while plt.fignum_exists(fig.number):
        try:
            rclpy.spin_once(node, timeout_sec=0.05)
        except Exception as exc:
            if "context is not valid" in str(exc):
                break
            raise

        # Mapa
        ax_map.clear()
        ix, iy = node.intruder_xy()
        node.intr_trail.append((ix, iy))

        # Geofence (igual que demo_viz por defecto)
        gf_n = [-120.0, -120.0, 220.0, 220.0, -120.0]
        gf_e = [-120.0, 120.0, 120.0, -120.0, -120.0]
        ax_map.plot(gf_e, gf_n, color="#3bd95f", lw=2.0, alpha=0.85, label="Geofence")

        if node.own_trail:
            o = np.array(node.own_trail)
            ax_map.plot(o[:, 0], o[:, 1], color="cyan", lw=1.5, alpha=0.6)
        if node.intr_trail:
            it = np.array(node.intr_trail)
            ax_map.plot(it[:, 0], it[:, 1], color="magenta", lw=1.2, alpha=0.55)

        ax_map.scatter([node.own_x], [node.own_y], c="cyan", s=60, label="Ownship")
        ax_map.scatter([ix], [iy], c="magenta", s=60, label="Intruder")
        ax_map.set_title("Mapa local EN (m)")
        ax_map.set_xlabel("E [m]")
        ax_map.set_ylabel("N [m]")
        ax_map.grid(True, alpha=0.25)
        ax_map.legend(loc="upper right")
        ax_map.set_aspect("equal", "box")
        ax_map.set_xlim(-180, 260)
        ax_map.set_ylim(-180, 260)
        ax_map.text(
            0.02,
            0.02,
            f"Own alt: {node.own_alt:.1f} m",
            transform=ax_map.transAxes,
            fontsize=9,
            color="white",
        )

        # Series
        t = np.array(node.history_t, dtype=float)
        c = np.array(node.history_conflict, dtype=float)
        h = np.array(node.history_min_h, dtype=float)
        v = np.array(node.history_min_v, dtype=float)

        ax_conf.clear()
        ax_conf.plot(t, c, color="orange")
        ax_conf.set_title("numConflictTraffic")
        ax_conf.set_ylim(-0.1, 2.5)
        ax_conf.grid(True, alpha=0.25)

        ax_minh.clear()
        ax_minh.plot(t, h, color="lime")
        ax_minh.set_title("minHDist [m]")
        ax_minh.grid(True, alpha=0.25)

        ax_minv.clear()
        ax_minv.plot(t, v, color="yellow")
        ax_minv.set_title("minVDist [m]")
        ax_minv.grid(True, alpha=0.25)

        ax_evt.clear()
        ax_evt.set_title("Alertas DAA")
        ax_evt.set_xlim(0, 1)
        ax_evt.set_ylim(0, 1)
        ax_evt.axis("off")
        y = 0.95
        if node.events:
            for ev in node.events:
                color = "#ff8c66" if "ENTER" in ev else "#7fd1ff"
                ax_evt.text(0.02, y, ev, fontsize=8.8, color=color, va="top", family="monospace")
                y -= 0.11
        else:
            ax_evt.text(0.02, 0.9, "Sin eventos aún", fontsize=9, color="#bbbbbb")

        plt.tight_layout()
        plt.pause(0.05)

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
