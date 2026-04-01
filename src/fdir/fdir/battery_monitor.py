"""FDIR-004: battery / fuel level thresholds."""

from __future__ import annotations


class BatteryMonitor:
    """FDIR-004: Monitor de nivel de batería/combustible."""

    def __init__(self, low_threshold: float = 0.30, critical_threshold: float = 0.10) -> None:
        self.low_threshold = low_threshold
        self.critical_threshold = critical_threshold
        self.level = 1.0

    def update(self, level: float) -> str | None:
        """Devuelve 'BATTERY_LOW', 'BATTERY_CRITICAL' o None."""
        self.level = float(level)
        if self.level <= self.critical_threshold:
            return "BATTERY_CRITICAL"
        if self.level <= self.low_threshold:
            return "BATTERY_LOW"
        return None
