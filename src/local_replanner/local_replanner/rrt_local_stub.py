"""REPL-010 placeholder: local RRT* window (500 m) — full planner hooks to GPP later."""

from __future__ import annotations

from typing import List, Sequence, Tuple


class RRTLocalStub:
    REPLAN_WINDOW_M = 500.0

    @staticmethod
    def bounds_around(position_ne: Sequence[float]) -> List[Tuple[float, float]]:
        n, e = float(position_ne[0]), float(position_ne[1])
        w = RRTLocalStub.REPLAN_WINDOW_M
        return [(n - w, n + w), (e - w, e + w)]
