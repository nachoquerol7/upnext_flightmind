"""FDIR-003: C2 link loss by heartbeat timeout."""

from __future__ import annotations

import time


class C2Monitor:
    """FDIR-003: Detector de pérdida de enlace C2."""

    def __init__(self, timeout_sec: float = 5.0) -> None:
        self.timeout_sec = timeout_sec
        self._last_heartbeat = time.monotonic()

    def heartbeat(self) -> None:
        self._last_heartbeat = time.monotonic()

    def check(self, now: float | None = None) -> bool:
        """True si el enlace está perdido (sin heartbeat dentro del timeout)."""
        t = time.monotonic() if now is None else now
        return (t - self._last_heartbeat) > self.timeout_sec
