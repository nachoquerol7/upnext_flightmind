"""M4 — Interfaz de localización SIL (TC-LOC-001 … TC-LOC-013)."""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest
import rclpy
from geometry_msgs.msg import Point, Quaternion
from nav_msgs.msg import Odometry
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Float64, String

_TEST_ROOT = Path(__file__).resolve().parents[1]
_MOCKS = _TEST_ROOT / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import fsm_input_injector  # noqa: E402
import mock_fastlio2  # noqa: E402

from mission_fsm.mission_fsm_node import MissionFsmNode


class _FsmModeCapture(Node):
    def __init__(self) -> None:
        super().__init__("fsm_mode_capture_m4")
        self.mode = ""
        self.trig = ""
        self.triggers: list[str] = []
        self.create_subscription(String, "/fsm/current_mode", self._on_mode, 10)
        self.create_subscription(String, "/fsm/active_trigger", self._on_trig, 10)

    def _on_mode(self, msg: String) -> None:
        self.mode = msg.data

    def _on_trig(self, msg: String) -> None:
        self.trig = msg.data
        if msg.data:
            self.triggers.append(msg.data)


def _spin_until(ex: MultiThreadedExecutor, pred: Callable[[], bool], *, timeout_sec: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        for _ in range(24):
            ex.spin_once(timeout_sec=0.02)
        if pred():
            return True
    return False


class _OdomCollector(Node):
    def __init__(self) -> None:
        super().__init__("tc_loc_odom_collector")
        self.received: list[Odometry] = []
        self.create_subscription(Odometry, "/Odometry", self._cb, 10)

    def _cb(self, msg: Odometry) -> None:
        self.received.append(msg)


class _FloatCollector(Node):
    def __init__(self, topic: str) -> None:
        super().__init__("tc_loc_float_collector")
        self.values: list[float] = []
        self.create_subscription(Float64, topic, self._cb, 10)

    def _cb(self, msg: Float64) -> None:
        self.values.append(float(msg.data))


def _spin_n(ex: MultiThreadedExecutor, n: int) -> None:
    for _ in range(n):
        ex.spin_once(timeout_sec=0.05)


@pytest.fixture
def mission_fsm_sil_with_fastlio(ros_context: None) -> SimpleNamespace:
    """Reusa patrón M1: FSM + inyector + captura + mock FastLIO2."""
    ex = MultiThreadedExecutor()
    fsm = MissionFsmNode()
    inj = fsm_input_injector.create_fsm_input_injector()
    cap = _FsmModeCapture()
    lio = mock_fastlio2.create_mock_fastlio2()
    for n in (fsm, inj, cap, lio):
        ex.add_node(n)

    def wait_mode(expected: str, *, timeout_sec: float = 3.0) -> bool:
        def _match() -> bool:
            m = cap.mode
            return m == expected or m.startswith(f"{expected}:")

        return _spin_until(ex, _match, timeout_sec=timeout_sec)

    h = SimpleNamespace(
        ex=ex,
        fsm=fsm,
        inj=inj,
        cap=cap,
        fastlio=lio,
        wait_mode=wait_mode,
        spin_until=lambda pred, timeout_sec=3.0: _spin_until(ex, pred, timeout_sec=timeout_sec),
    )
    yield h
    for n in (fsm, inj, cap, lio):
        ex.remove_node(n)
        n.destroy_node()


def _reach_cruise(h: SimpleNamespace) -> None:
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    h.inj.inject("takeoff_complete", True)
    assert h.wait_mode("CRUISE")


def test_tc_loc001_odometry_topic_delivers_nav_msgs_odometry(ros_context: None) -> None:
    """TC-LOC-001: /Odometry entrega al menos un nav_msgs/Odometry del mock."""
    ex = MultiThreadedExecutor()
    lio = mock_fastlio2.create_mock_fastlio2()
    sub = _OdomCollector()
    ex.add_node(lio)
    ex.add_node(sub)
    _spin_n(ex, 40)
    ex.remove_node(lio)
    ex.remove_node(sub)
    lio.destroy_node()
    sub.destroy_node()
    assert len(sub.received) >= 1 and isinstance(sub.received[-1], Odometry)


def test_tc_loc002_quality_flag_inject_updates_published_float64(ros_context: None) -> None:
    """TC-LOC-002: inject('quality_flag', v) se refleja en /quality_flag (Float64)."""
    ex = MultiThreadedExecutor()
    lio = mock_fastlio2.create_mock_fastlio2()
    sub = _FloatCollector("/quality_flag")
    ex.add_node(lio)
    ex.add_node(sub)
    lio.inject("quality_flag", 0.42)
    _spin_n(ex, 30)
    ex.remove_node(lio)
    ex.remove_node(sub)
    lio.destroy_node()
    sub.destroy_node()
    assert any(math.isclose(v, 0.42) for v in sub.values)


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.8: no hay nodo monitor que exija /Odometry con timeout configurable",
    strict=True,
)
def test_tc_loc003_odometry_absence_exceeding_timeout_raises_fault(ros_context: None) -> None:
    """TC-LOC-003: ausencia prolongada de /Odometry dispara fallo localización."""
    # GAP-ARCH-1.8: aquí iría aserción sobre modo FAULT o topic de salud del monitor.
    assert False


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.8: no hay monitor de discontinuidad de pose en el stack SIL actual",
    strict=True,
)
def test_tc_loc004_pose_jump_triggers_discontinuity_alert(ros_context: None) -> None:
    """TC-LOC-004: salto brusco de pose genera alerta de discontinuidad."""
    # GAP-ARCH-1.8: monitor de salto de pose no implementado frente a /Odometry.
    assert False


def test_tc_loc005_inject_odometry_pose_updates_position(ros_context: None) -> None:
    """TC-LOC-005: inject('odometry', msg) actualiza posición publicada."""
    ex = MultiThreadedExecutor()
    lio = mock_fastlio2.create_mock_fastlio2()
    sub = _OdomCollector()
    ex.add_node(lio)
    ex.add_node(sub)
    odom = Odometry()
    odom.pose.pose.position = Point(x=10.0, y=2.0, z=0.0)
    odom.pose.pose.orientation = Quaternion(w=1.0)
    lio.inject("odometry", odom)
    _spin_n(ex, 25)
    ex.remove_node(lio)
    ex.remove_node(sub)
    lio.destroy_node()
    sub.destroy_node()
    assert sub.received and abs(sub.received[-1].pose.pose.position.x - 10.0) < 1e-6


def test_tc_loc006_low_quality_via_fastlio_drives_fsm_to_event(mission_fsm_sil_with_fastlio: SimpleNamespace) -> None:
    """TC-LOC-006: calidad baja vía mock_fastlio2 → /fsm/in/quality_flag → EVENT."""
    _reach_cruise(mission_fsm_sil_with_fastlio)
    mission_fsm_sil_with_fastlio.fastlio.inject("quality_flag", 0.1)
    assert mission_fsm_sil_with_fastlio.wait_mode("EVENT") and "to_event" in mission_fsm_sil_with_fastlio.cap.triggers


def test_tc_loc007_nominal_quality_keeps_cruise(mission_fsm_sil_with_fastlio: SimpleNamespace) -> None:
    """TC-LOC-007: quality_flag alto no provoca EVENT desde CRUISE (sin otras señales)."""
    _reach_cruise(mission_fsm_sil_with_fastlio)
    mission_fsm_sil_with_fastlio.fastlio.inject("quality_flag", 1.0)
    for _ in range(40):
        mission_fsm_sil_with_fastlio.ex.spin_once(timeout_sec=0.05)
    assert mission_fsm_sil_with_fastlio.fsm._fsm.state == "CRUISE"  # noqa: SLF001


def test_tc_loc008_odometry_header_frame_id_is_map(ros_context: None) -> None:
    """TC-LOC-008: frame_id de odometría del mock es coherente (map)."""
    ex = MultiThreadedExecutor()
    lio = mock_fastlio2.create_mock_fastlio2()
    sub = _OdomCollector()
    ex.add_node(lio)
    ex.add_node(sub)
    _spin_n(ex, 15)
    ex.remove_node(lio)
    ex.remove_node(sub)
    lio.destroy_node()
    sub.destroy_node()
    assert sub.received[-1].header.frame_id == "map"


def test_tc_loc009_mock_publishes_odometry_repeatedly(ros_context: None) -> None:
    """TC-LOC-009: el mock emite más de un mensaje /Odometry en ventana corta."""
    ex = MultiThreadedExecutor()
    lio = mock_fastlio2.create_mock_fastlio2()
    sub = _OdomCollector()
    ex.add_node(lio)
    ex.add_node(sub)
    _spin_n(ex, 60)
    ex.remove_node(lio)
    ex.remove_node(sub)
    lio.destroy_node()
    sub.destroy_node()
    assert len(sub.received) >= 2


def test_tc_loc010_quality_at_threshold_not_degraded(mission_fsm_sil_with_fastlio: SimpleNamespace) -> None:
    """TC-LOC-010: quality_flag == umbral (0.5) no cumple quality_degraded (<)."""
    _reach_cruise(mission_fsm_sil_with_fastlio)
    mission_fsm_sil_with_fastlio.fastlio.inject("quality_flag", 0.5)
    for _ in range(50):
        mission_fsm_sil_with_fastlio.ex.spin_once(timeout_sec=0.05)
    assert mission_fsm_sil_with_fastlio.fsm._fsm.state == "CRUISE"  # noqa: SLF001 — cap.mode puede rezagarse


def test_tc_loc011_quality_slightly_below_threshold_goes_event(mission_fsm_sil_with_fastlio: SimpleNamespace) -> None:
    """TC-LOC-011: quality_flag justo bajo umbral → EVENT."""
    _reach_cruise(mission_fsm_sil_with_fastlio)
    mission_fsm_sil_with_fastlio.fastlio.inject("quality_flag", 0.499)
    assert mission_fsm_sil_with_fastlio.wait_mode("EVENT")


@pytest.mark.xfail(
    reason="XFAIL-ARCH-1.8: no hay publicación de alerta de discontinuidad ante salto de pose",
    strict=True,
)
def test_tc_loc012_large_pose_jump_without_monitor_does_not_surface_ros_alert(ros_context: None) -> None:
    """TC-LOC-012: salto grande de pose debería ser visible para un monitor (ausente)."""
    ex = MultiThreadedExecutor()
    lio = mock_fastlio2.create_mock_fastlio2()
    sub = _OdomCollector()
    ex.add_node(lio)
    ex.add_node(sub)
    jump = Odometry()
    jump.pose.pose.position = Point(x=1e6, y=0.0, z=0.0)
    jump.pose.pose.orientation.w = 1.0
    lio.inject("odometry", jump)
    _spin_n(ex, 20)
    ex.remove_node(lio)
    ex.remove_node(sub)
    lio.destroy_node()
    sub.destroy_node()
    # Sin monitor, no existe topic de alerta; el test documenta el gap vía xfail.
    assert hasattr(sub.received[-1], "pose_jump_alert")  # nunca


def test_tc_loc013_end_to_end_fastlio_quality_to_fsm_trigger_chain(mission_fsm_sil_with_fastlio: SimpleNamespace) -> None:
    """TC-LOC-013: cadena mock_fastlio2.inject(quality) → to_event en historial FSM."""
    _reach_cruise(mission_fsm_sil_with_fastlio)
    n0 = len(mission_fsm_sil_with_fastlio.cap.triggers)
    mission_fsm_sil_with_fastlio.fastlio.inject("quality_flag", 0.0)
    assert mission_fsm_sil_with_fastlio.spin_until(
        lambda: len(mission_fsm_sil_with_fastlio.cap.triggers) > n0
        and "to_event" in mission_fsm_sil_with_fastlio.cap.triggers,
        timeout_sec=5.0,
    )
