"""TC-FDIR-C01..C03 — C2Monitor heartbeat timeout."""

from __future__ import annotations

import time

from fdir.c2_monitor import C2Monitor


def test_tc_fdir_c01_timeout_reports_lost() -> None:
    m = C2Monitor(timeout_sec=0.05)
    time.sleep(0.12)
    assert m.check() is True


def test_tc_fdir_c02_heartbeat_resets() -> None:
    m = C2Monitor(timeout_sec=1.0)
    m.heartbeat()
    assert m.check() is False


def test_tc_fdir_c03_not_lost_immediately_after_heartbeat() -> None:
    m = C2Monitor(timeout_sec=0.2)
    m.heartbeat()
    time.sleep(0.05)
    assert m.check() is False
