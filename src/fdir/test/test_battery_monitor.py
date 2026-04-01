"""TC-FDIR-B01..B05 — BatteryMonitor thresholds."""

from __future__ import annotations

from fdir.battery_monitor import BatteryMonitor


def test_tc_fdir_b01_low_at_30_percent() -> None:
    m = BatteryMonitor(low_threshold=0.30, critical_threshold=0.10)
    assert m.update(0.30) == "BATTERY_LOW"


def test_tc_fdir_b02_critical_at_10_percent() -> None:
    m = BatteryMonitor(low_threshold=0.30, critical_threshold=0.10)
    assert m.update(0.10) == "BATTERY_CRITICAL"


def test_tc_fdir_b03_no_alarm_at_50_percent() -> None:
    m = BatteryMonitor(low_threshold=0.30, critical_threshold=0.10)
    assert m.update(0.50) is None


def test_tc_fdir_b04_critical_overrides_low() -> None:
    m = BatteryMonitor(low_threshold=0.30, critical_threshold=0.10)
    assert m.update(0.05) == "BATTERY_CRITICAL"


def test_tc_fdir_b05_level_stored() -> None:
    m = BatteryMonitor()
    m.update(0.42)
    assert m.level == 0.42
