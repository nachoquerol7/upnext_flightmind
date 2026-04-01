"""Dashboard matplotlib: mapa EN, bandas DAA, log CONFLICT ENTER/CLEAR."""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from typing import Any, Deque, List, Tuple

import rclpy
from flightmind_msgs.msg import TrafficReport
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray, String


class DaaDashboardNode(Node):
    def __init__(self) -> None:
        super().__init__("daa_dashboard")
        self._n = self._e = 0.0
        self._trail_own: Deque[Tuple[float, float]] = deque(maxlen=400)
        self._intr_xy: List[Tuple[float, float]] = []
        self._polys: List[List[Tuple[float, float]]] = []
        self._bands = [0.0, 1e9, 1e9]
        self._last_conflict = 0.0
        self._log: List[str] = []
        self._lock = threading.Lock()

        self.create_subscription(Float64MultiArray, "/ownship/state", self._on_own, 10)
        self.create_subscription(TrafficReport, "/traffic/intruders", self._on_tr, 10)
        self.create_subscription(Float64MultiArray, "/daidalus/bands_summary", self._on_b, 10)
        self.create_subscription(String, "/airspace/geofences", self._on_geo, 10)

    def _on_own(self, msg: Float64MultiArray) -> None:
        if len(msg.data) < 2:
            return
        with self._lock:
            self._n = float(msg.data[0])
            self._e = float(msg.data[1])
            self._trail_own.append((self._e, self._n))

    def _on_tr(self, msg: TrafficReport) -> None:
        with self._lock:
            self._intr_xy = [(float(i.e_m), float(i.n_m)) for i in msg.intruders]

    def _on_b(self, msg: Float64MultiArray) -> None:
        if len(msg.data) < 3:
            return
        with self._lock:
            nc = float(msg.data[0])
            prev = self._last_conflict
            self._bands = [nc, float(msg.data[1]), float(msg.data[2])]
            if nc >= 1.0 and prev < 1.0:
                self._log.append(f"CONFLICT ENTER  t={time.time():.3f}  n={nc:.0f}")
            if nc < 1.0 and prev >= 1.0:
                self._log.append(f"CONFLICT CLEAR   t={time.time():.3f}  n={nc:.0f}")
            self._last_conflict = nc
            self._log = self._log[-12:]

    def _on_geo(self, msg: String) -> None:
        try:
            data = json.loads(msg.data) if msg.data.strip() else {}
            raw = data.get("polygons", [])
            polys: List[List[Tuple[float, float]]] = []
            for p in raw:
                if isinstance(p, list) and len(p) >= 3:
                    polys.append([(float(q[1]), float(q[0])) for q in p])
            with self._lock:
                self._polys = polys
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    def snapshot(self) -> Any:
        with self._lock:
            return (
                list(self._trail_own),
                list(self._intr_xy),
                [list(p) for p in self._polys],
                list(self._bands),
                list(self._log),
            )


def main() -> None:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    rclpy.init()
    node = DaaDashboardNode()
    ex = MultiThreadedExecutor()
    ex.add_node(node)
    th = threading.Thread(target=ex.spin, daemon=True)
    th.start()

    fig = plt.figure(figsize=(11, 9))
    gs = fig.add_gridspec(2, 2)
    ax_map = fig.add_subplot(gs[0, 0])
    ax_bands = fig.add_subplot(gs[0, 1])
    ax_log = fig.add_subplot(gs[1, :])
    ax_log.axis("off")

    def update(_frame: int) -> None:
        trail, intrs, polys, bands, log = node.snapshot()
        ax_map.clear()
        ax_map.set_title("Mapa EN (x=E, y=N) + geocercas")
        ax_map.set_xlabel("E (m)")
        ax_map.set_ylabel("N (m)")
        ax_map.set_aspect("equal", adjustable="box")
        for poly in polys:
            if poly:
                xs = [p[0] for p in poly] + [poly[0][0]]
                ys = [p[1] for p in poly] + [poly[0][1]]
                ax_map.fill(xs, ys, alpha=0.2, color="red", edgecolor="darkred")
        if trail:
            te, tn = zip(*trail)
            ax_map.plot(te, tn, "b-", linewidth=1.2, label="ownship")
            ax_map.scatter([te[-1]], [tn[-1]], c="blue", s=40, zorder=5)
        for i, (ie, inn) in enumerate(intrs):
            ax_map.scatter([ie], [inn], c="orange", s=50, marker="^", zorder=6)
        ax_map.legend(loc="upper right", fontsize=8)

        ax_bands.clear()
        ax_bands.set_title("DAA bands_summary")
        ax_bands.bar(["numConflict", "minH", "minV"], bands[:3], color=["crimson", "steelblue", "seagreen"])
        ax_bands.set_ylabel("valor")

        ax_log.clear()
        ax_log.axis("off")
        ax_log.set_title("Alertas")
        txt = "\n".join(log) if log else "(sin transiciones)"
        ax_log.text(0.02, 0.95, txt, transform=ax_log.transAxes, va="top", family="monospace", fontsize=9)

    _ani = FuncAnimation(fig, update, interval=250, cache_frame_data=False)
    plt.tight_layout()
    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        ex.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
