"""Informed-RRT* in SE2 with Dubins edges and polygon NFZ (NED NE)."""

from __future__ import annotations

import hashlib
import logging
import math
import random
from typing import List, Sequence, Tuple

from gpp.dubins import dubins_interpolate, dubins_length
from gpp.geometry import point_in_polygon, segment_hits_nfz

_logger = logging.getLogger(__name__)

State = Tuple[float, float, float]  # n, e, heading rad
Polygon = Sequence[Tuple[float, float]]


def _wrap(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _dist_se2(a: State, b: State) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1]) + 0.3 * abs(_wrap(a[2] - b[2]))


def _dubins_collision(
    a: State,
    b: State,
    rho: float,
    nfz: Sequence[Polygon],
    samples: int = 28,
) -> bool:
    ln, fn = dubins_interpolate(a[0], a[1], a[2], b[0], b[1], b[2], rho)
    if ln >= 1e8:
        return True
    for i in range(samples + 1):
        s = ln * i / samples
        n, e, _ = fn(s)
        for poly in nfz:
            if point_in_polygon(n, e, poly):
                return True
    return False


class RRTStarPlanner:
    """RRT*-style tree with Dubins steering; informed sampling after first solution."""

    def __init__(
        self,
        turn_radius_m: float,
        *,
        max_iter: int = 1200,
        step_size_m: float = 55.0,
        goal_bias: float = 0.18,
        seed: int = 42,
    ) -> None:
        self.rho = max(turn_radius_m, 1.0)
        self.max_iter = max_iter
        self.step_size = step_size_m
        self.goal_bias = goal_bias
        self._rng = random.Random(seed)
        self._last_path: List[State] = []
        self._goal_key: str = ""
        self._last_start: State = (0.0, 0.0, 0.0)
        self.replan_calls = 0

    @staticmethod
    def goal_nfz_key(goal: Sequence[float], nfz_json: str) -> str:
        g = ",".join(f"{float(x):.6f}" for x in goal)
        return hashlib.sha256((g + "|" + nfz_json).encode()).hexdigest()[:24]

    def plan_if_needed(
        self,
        start: State,
        goal: State,
        nfz: Sequence[Polygon],
        bounds: Tuple[float, float, float, float],
        goal_tuple: Sequence[float],
        nfz_json: str,
    ) -> List[State]:
        gk = self.goal_nfz_key(goal_tuple, nfz_json)
        if gk == self._goal_key and gk != "":
            return list(self._last_path)
        self.replan_calls += 1
        self._goal_key = gk
        path = self._plan(start, goal, nfz, bounds)
        if len(path) < 2:
            # No safe path found, return start only and keep cache coherent.
            self._last_path = [start]
            return [start]
        self._last_path = path
        return list(path)

    def _sample(
        self,
        bounds: Tuple[float, float, float, float],
        goal: State,
        best_cost: float,
        informed: bool,
    ) -> State:
        nmin, nmax, emin, emax = bounds
        if informed and best_cost < 1e8:
            cx = (goal[0] + self._last_start[0]) / 2.0
            cy = (goal[1] + self._last_start[1]) / 2.0
            rx = min(best_cost * 0.55, (nmax - nmin) / 2.0)
            ry = min(best_cost * 0.55, (emax - emin) / 2.0)
            n = cx + (self._rng.random() * 2.0 - 1.0) * rx
            e = cy + (self._rng.random() * 2.0 - 1.0) * ry
        else:
            n = nmin + self._rng.random() * (nmax - nmin)
            e = emin + self._rng.random() * (emax - emin)
        h = -math.pi + 2.0 * math.pi * self._rng.random()
        return (n, e, h)

    def _steer(self, from_s: State, to_s: State) -> State:
        L = dubins_length(from_s[0], from_s[1], from_s[2], to_s[0], to_s[1], to_s[2], self.rho)
        if L >= 1e8:
            return from_s
        if L <= self.step_size:
            return to_s
        ln, fn = dubins_interpolate(from_s[0], from_s[1], from_s[2], to_s[0], to_s[1], to_s[2], self.rho)
        return fn(self.step_size)

    def _dense_dubins_fallback(self, start: State, goal: State, samples: int = 48) -> List[State]:
        """Sample Dubins edge for visualization / execution when a straight chord would cross NFZ."""
        ln, fn = dubins_interpolate(start[0], start[1], start[2], goal[0], goal[1], goal[2], self.rho)
        if ln >= 1e8:
            return [start]
        return [fn(ln * i / samples) for i in range(samples + 1)]

    def _plan(self, start: State, goal: State, nfz: Sequence[Polygon], bounds: Tuple[float, float, float, float]) -> List[State]:
        self._last_start = start
        nodes: List[State] = [start]
        parent: List[int] = [-1]
        cost: List[float] = [0.0]
        best_goal_idx: int | None = None
        best_cost = float("inf")
        informed = False

        for _ in range(self.max_iter):
            if self._rng.random() < self.goal_bias:
                x_rand = goal
            else:
                x_rand = self._sample(bounds, goal, best_cost, informed)

            idx_near = min(range(len(nodes)), key=lambda i: _dist_se2(nodes[i], x_rand))
            x_new = self._steer(nodes[idx_near], x_rand)
            if _dubins_collision(nodes[idx_near], x_new, self.rho, nfz):
                continue

            gamma = 60.0
            card = len(nodes)
            r = min(gamma * math.sqrt(math.log(card + 1) / (card + 1)), self.step_size * 4.0)
            near_idx = [i for i in range(len(nodes)) if _dist_se2(nodes[i], x_new) < r]

            best_p = idx_near
            el = dubins_length(
                nodes[idx_near][0],
                nodes[idx_near][1],
                nodes[idx_near][2],
                x_new[0],
                x_new[1],
                x_new[2],
                self.rho,
            )
            if el >= 1e8:
                continue
            best_pc = cost[idx_near] + el
            for j in near_idx:
                c_edge = dubins_length(
                    nodes[j][0], nodes[j][1], nodes[j][2], x_new[0], x_new[1], x_new[2], self.rho
                )
                if c_edge >= 1e8:
                    continue
                c = cost[j] + c_edge
                if c < best_pc and not _dubins_collision(nodes[j], x_new, self.rho, nfz):
                    best_pc = c
                    best_p = j

            parent.append(best_p)
            nodes.append(x_new)
            cost.append(best_pc)
            new_i = len(nodes) - 1

            dg = dubins_length(x_new[0], x_new[1], x_new[2], goal[0], goal[1], goal[2], self.rho)
            if dg < 80.0 and not _dubins_collision(x_new, goal, self.rho, nfz):
                tc = best_pc + dg
                if tc < best_cost:
                    best_cost = tc
                    best_goal_idx = new_i
                    informed = True

        if best_goal_idx is None:
            # Fallback: Dubins edge [start, goal] only if collision-free
            if not _dubins_collision(start, goal, self.rho, nfz):
                # FIX-GPP-G03: do not publish only two poses if the straight chord pierces NFZ
                if segment_hits_nfz(start[0], start[1], goal[0], goal[1], nfz):
                    _logger.warning(
                        "WARNING: RRT* failed and direct path hits NFZ — no safe path found; "
                        "using Dubins-sampled path"
                    )
                    return self._dense_dubins_fallback(start, goal)
                return [start, goal]
            return [start]  # no safe path found

        chain: List[int] = []
        i: int | None = best_goal_idx
        while i is not None and i >= 0:
            chain.append(i)
            i = parent[i]
        chain.reverse()
        path = [nodes[k] for k in chain]
        if path[-1] != goal:
            path.append(goal)
        return path
