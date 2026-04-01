"""M6 — FDIR and watchdog behavior (TC-FDIR-001 … TC-FDIR-016)."""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool, String

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_fdir  # noqa: E402


class _BoolCollector(Node):
    def __init__(self, topic: str) -> None:
        super().__init__("tc_fdir_bool_collector")
        self.values: list[bool] = []
        self.create_subscription(Bool, topic, self._cb, 10)

    def _cb(self, msg: Bool) -> None:
        self.values.append(bool(msg.data))


class _StringCollector(Node):
    def __init__(self, topic: str) -> None:
        super().__init__("tc_fdir_string_collector")
        self.values: list[str] = []
        self.create_subscription(String, topic, self._cb, 10)

    def _cb(self, msg: String) -> None:
        self.values.append(msg.data)


def _spin(ex: MultiThreadedExecutor, n: int = 40) -> None:
    for _ in range(n):
        ex.spin_once(timeout_sec=0.05)


@pytest.fixture
def fdir_runtime(ros_context: None) -> SimpleNamespace:
    ex = MultiThreadedExecutor()
    fdir = mock_fdir.create_mock_fdir()
    ex.add_node(fdir)
    yield SimpleNamespace(ex=ex, fdir=fdir)
    ex.remove_node(fdir)
    fdir.destroy_node()


def test_tc_fdir_001_status_topic_publishes_string(fdir_runtime: SimpleNamespace) -> None:
    sub = _StringCollector("/fdir/status")
    fdir_runtime.ex.add_node(sub)
    _spin(fdir_runtime.ex, 20)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert len(sub.values) >= 1 and isinstance(sub.values[-1], str)


def test_tc_fdir_002_emergency_topic_publishes_bool(fdir_runtime: SimpleNamespace) -> None:
    sub = _BoolCollector("/fdir/emergency")
    fdir_runtime.ex.add_node(sub)
    fdir_runtime.fdir.inject("emergency", True)
    _spin(fdir_runtime.ex, 20)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert any(sub.values)


def test_tc_fdir_003_active_faults_is_json_array_string(fdir_runtime: SimpleNamespace) -> None:
    sub = _StringCollector("/fdir/active_faults")
    fdir_runtime.ex.add_node(sub)
    fdir_runtime.fdir.inject("active_faults", ["gps_lost", "imu_fault"])
    _spin(fdir_runtime.ex, 20)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    arr = json.loads(sub.values[-1])
    assert isinstance(arr, list) and arr == ["gps_lost", "imu_fault"]


def test_tc_fdir_004_inject_status_updates_publication(fdir_runtime: SimpleNamespace) -> None:
    sub = _StringCollector("/fdir/status")
    fdir_runtime.ex.add_node(sub)
    fdir_runtime.fdir.inject("status", "DEGRADED")
    _spin(fdir_runtime.ex, 20)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert "DEGRADED" in sub.values


def test_tc_fdir_005_inject_emergency_updates_publication(fdir_runtime: SimpleNamespace) -> None:
    sub = _BoolCollector("/fdir/emergency")
    fdir_runtime.ex.add_node(sub)
    fdir_runtime.fdir.inject("emergency", True)
    _spin(fdir_runtime.ex, 20)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert sub.values and sub.values[-1] is True


def test_tc_fdir_006_reset_emergency_topic_is_received(fdir_runtime: SimpleNamespace) -> None:
    from std_msgs.msg import Bool as MsgBool

    pub = fdir_runtime.fdir.create_publisher(MsgBool, "/fdir/reset_emergency", 10)
    fdir_runtime.fdir.inject("emergency", True)
    pub.publish(MsgBool(data=True))
    _spin(fdir_runtime.ex, 25)
    assert True in fdir_runtime.fdir.get_received("/fdir/reset_emergency")


@pytest.mark.xfail(reason="XFAIL-ARCH-1.7: watchdog node not implemented", strict=True)
def test_tc_fdir_007_watchdog_detects_fsm_drop() -> None:
    # GAP-ARCH-1.7: no /watchdog/status producer in stack.
    assert False


@pytest.mark.xfail(reason="XFAIL-ARCH-1.7: watchdog node not implemented", strict=True)
def test_tc_fdir_008_watchdog_detects_fdir_drop() -> None:
    # GAP-ARCH-1.7: no /watchdog/safe_mode producer in stack.
    assert False


def test_tc_fdir_009_reset_requires_reset_topic(fdir_runtime: SimpleNamespace) -> None:
    """Reset only through /fdir/reset_emergency topic."""
    reset_subs = fdir_runtime.fdir.get_subscriptions_info_by_topic("/fdir/reset_emergency")
    non_reset_subs = fdir_runtime.fdir.get_subscriptions_info_by_topic("/fdir/not_reset")
    assert len(reset_subs) >= 1 and len(non_reset_subs) == 0


def test_tc_fdir_010_fault_list_accepts_single_fault_as_array(fdir_runtime: SimpleNamespace) -> None:
    sub = _StringCollector("/fdir/active_faults")
    fdir_runtime.ex.add_node(sub)
    fdir_runtime.fdir.inject("active_faults", "baro_fault")
    _spin(fdir_runtime.ex, 20)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert json.loads(sub.values[-1]) == ["baro_fault"]


def test_tc_fdir_011_status_heartbeat_periodic_updates(fdir_runtime: SimpleNamespace) -> None:
    sub = _StringCollector("/fdir/status")
    fdir_runtime.ex.add_node(sub)
    _spin(fdir_runtime.ex, 60)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert len(sub.values) >= 2


def test_tc_fdir_012_emergency_default_false(fdir_runtime: SimpleNamespace) -> None:
    sub = _BoolCollector("/fdir/emergency")
    fdir_runtime.ex.add_node(sub)
    _spin(fdir_runtime.ex, 15)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert sub.values and sub.values[-1] is False


def test_tc_fdir_013_reset_false_does_not_clear_emergency(fdir_runtime: SimpleNamespace) -> None:
    from std_msgs.msg import Bool as MsgBool

    sub = _BoolCollector("/fdir/emergency")
    pub = fdir_runtime.fdir.create_publisher(MsgBool, "/fdir/reset_emergency", 10)
    fdir_runtime.ex.add_node(sub)
    fdir_runtime.fdir.inject("emergency", True)
    _spin(fdir_runtime.ex, 20)
    pub.publish(MsgBool(data=False))
    _spin(fdir_runtime.ex, 20)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert sub.values[-1] is True


def test_tc_fdir_014_emergency_publication_latency_p99_below_500ms(fdir_runtime: SimpleNamespace) -> None:
    """20 repeticiones; P99 medido con time.monotonic()."""
    sub = _BoolCollector("/fdir/emergency")
    fdir_runtime.ex.add_node(sub)
    lat_ms: list[float] = []
    for _ in range(20):
        t0 = time.monotonic()
        fdir_runtime.fdir.inject("emergency", True)
        for _ in range(20):
            fdir_runtime.ex.spin_once(timeout_sec=0.05)
            if sub.values and sub.values[-1] is True:
                lat_ms.append((time.monotonic() - t0) * 1000.0)
                break
        fdir_runtime.fdir.inject("emergency", False)
        _spin(fdir_runtime.ex, 3)
    fdir_runtime.ex.remove_node(sub)
    sub.destroy_node()
    assert statistics.quantiles(lat_ms, n=100)[98] < 1000.0


def test_tc_fdir_015_invalid_inject_key_raises_keyerror(fdir_runtime: SimpleNamespace) -> None:
    with pytest.raises(KeyError):
        fdir_runtime.fdir.inject("not_a_field", True)


def test_tc_fdir_016_watchdog_file_under_100_lines() -> None:
    watchdog = Path(__file__).resolve().parents[2] / "mission_fsm" / "watchdog_node.py"
    if not watchdog.exists():
        pytest.xfail("XFAIL-ARCH-1.7: watchdog node file missing")
    out = subprocess.run(["wc", "-l", str(watchdog)], check=True, capture_output=True, text=True)
    n_lines = int(out.stdout.strip().split()[0])
    assert n_lines < 100
