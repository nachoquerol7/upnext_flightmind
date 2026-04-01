"""TC-REPL-001..004 (stub coverage)."""

from __future__ import annotations

import pytest

from local_replanner.rrt_local_stub import RRTLocalStub


@pytest.mark.no_ros
def test_tc_repl_001_window_500m() -> None:
    assert RRTLocalStub.REPLAN_WINDOW_M == 500.0


@pytest.mark.no_ros
def test_tc_repl_002_bounds_symmetric() -> None:
    b = RRTLocalStub.bounds_around((100.0, 200.0))
    assert b[0][0] == pytest.approx(100.0 - 500.0)
    assert b[1][1] == pytest.approx(200.0 + 500.0)


@pytest.mark.no_ros
def test_tc_repl_003_stub_instantiable() -> None:
    assert RRTLocalStub.bounds_around((0, 0))


@pytest.mark.no_ros
def test_tc_repl_004_timeout_placeholder() -> None:
    assert RRTLocalStub.REPLAN_WINDOW_M > 0.0
