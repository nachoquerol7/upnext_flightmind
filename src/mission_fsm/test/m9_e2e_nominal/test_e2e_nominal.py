"""M9 — E2E nominal missions (TC-E2E-001 … TC-E2E-010)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from flightmind_msgs.msg import FSMState
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

_MOCKS = Path(__file__).resolve().parents[1] / "mocks"
if str(_MOCKS) not in sys.path:
    sys.path.insert(0, str(_MOCKS))

import mock_daidalus  # noqa: E402
import mock_fastlio2  # noqa: E402
import mock_fdir  # noqa: E402
import mock_nav2  # noqa: E402
import mock_sensors  # noqa: E402

from mission_fsm.fsm import default_inputs  # noqa: E402


class _FSMStateCollector(Node):
    def __init__(self) -> None:
        super().__init__("tc_e2e_fsm_state_collector")
        self.msgs: list[FSMState] = []
        self.create_subscription(FSMState, "/fsm/state", self._cb, 10)

    def _cb(self, msg: FSMState) -> None:
        self.msgs.append(msg)


def _spin(ex: MultiThreadedExecutor, n: int = 40) -> None:
    for _ in range(n):
        ex.spin_once(timeout_sec=0.05)


def _reach_cruise(h: SimpleNamespace) -> None:
    h.inj.inject("preflight_ok", True)
    assert h.wait_mode("AUTOTAXI")
    h.inj.inject("taxi_clear", True)
    assert h.wait_mode("TAKEOFF")
    h.inj.inject("takeoff_complete", True)
    assert h.wait_mode("CRUISE")


@pytest.fixture
def e2e_runtime(mission_fsm_sil_harness: SimpleNamespace) -> SimpleNamespace:
    ex = mission_fsm_sil_harness.ex
    fsm_state_sub = _FSMStateCollector()
    lio = mock_fastlio2.create_mock_fastlio2()
    dai = mock_daidalus.create_mock_daidalus()
    fdir = mock_fdir.create_mock_fdir()
    nav = mock_nav2.create_mock_nav2()
    sens = mock_sensors.create_mock_sensors()
    for n in (fsm_state_sub, lio, dai, fdir, nav, sens):
        ex.add_node(n)
    h = SimpleNamespace(**vars(mission_fsm_sil_harness))
    h.fsm_state_sub = fsm_state_sub
    h.fastlio = lio
    h.daidalus = dai
    h.fdir = fdir
    h.nav2 = nav
    h.sensors = sens
    yield h
    for n in (fsm_state_sub, lio, dai, fdir, nav, sens):
        ex.remove_node(n)
        n.destroy_node()


def test_tc_e2e_001_nominal_mission_reaches_cruise(e2e_runtime: SimpleNamespace) -> None:
    _reach_cruise(e2e_runtime)
    assert e2e_runtime.fsm_state_sub.msgs and e2e_runtime.fsm_state_sub.msgs[-1].current_mode == "CRUISE"


def test_tc_e2e_002_nominal_landing_path(e2e_runtime: SimpleNamespace) -> None:
    _reach_cruise(e2e_runtime)
    e2e_runtime.inj.inject("land_command", True)
    assert e2e_runtime.wait_mode("LANDING")


def test_tc_e2e_003_vtol_config_exists_and_has_required_params() -> None:
    p = Path(__file__).resolve().parents[2] / "config" / "mission_fsm_vtol.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    rp = data["mission_fsm_node"]["ros__parameters"]
    assert rp["go_around_max_attempts"] == 3 and rp["takeoff_max_duration_sec"] == 60


def test_tc_e2e_004_heli_config_exists_and_has_required_params() -> None:
    p = Path(__file__).resolve().parents[2] / "config" / "mission_fsm_heli.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["mission_fsm_node"]["ros__parameters"]["go_around_max_attempts"] == 5


def test_tc_e2e_005_male_config_exists_and_has_required_params() -> None:
    p = Path(__file__).resolve().parents[2] / "config" / "mission_fsm_male.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    rp = data["mission_fsm_node"]["ros__parameters"]
    assert rp["c2_timeout_sec"] == 30 and rp["bvlos_mode"] is True


def test_tc_e2e_006_repeated_nominal_transition_stability(e2e_runtime: SimpleNamespace) -> None:
    for _ in range(3):
        e2e_runtime.fsm._fsm.reset("PREFLIGHT")
        e2e_runtime.fsm._inputs = default_inputs()  # noqa: SLF001 — evitar saltar PREFLIGHT/AUTOTAXI por inputs rezagados
        _reach_cruise(e2e_runtime)
    assert e2e_runtime.cap.mode == "CRUISE"


def test_tc_e2e_007_memory_growth_under_10mb_across_5_missions(e2e_runtime: SimpleNamespace) -> None:
    psutil = pytest.importorskip("psutil")
    proc = psutil.Process(os.getpid())
    rss0 = proc.memory_info().rss
    for _ in range(5):
        e2e_runtime.fsm._fsm.reset("PREFLIGHT")
        e2e_runtime.fsm._inputs = default_inputs()  # noqa: SLF001
        for _cmd in ("land_command", "abort_command", "rtb_command"):
            e2e_runtime.inj.inject(_cmd, False)
        _reach_cruise(e2e_runtime)
        e2e_runtime.inj.inject("land_command", True)
        _spin(e2e_runtime.ex, 10)
    rss1 = proc.memory_info().rss
    assert (rss1 - rss0) < (10 * 1024 * 1024)


def test_tc_e2e_008_fsm_state_contract_used_in_e2e(e2e_runtime: SimpleNamespace) -> None:
    _reach_cruise(e2e_runtime)
    _spin(e2e_runtime.ex, 40)
    assert any(hasattr(m, "current_mode") and hasattr(m, "active_trigger") for m in e2e_runtime.fsm_state_sub.msgs)


@pytest.mark.xfail(reason="XFAIL-ARCH-1.10: black box logger not implemented", strict=True)
def test_tc_e2e_009_blackbox_log_written_for_nominal_mission() -> None:
    assert Path("/tmp/flightmind_blackbox.log").exists()


@pytest.mark.xfail(reason="XFAIL-ARCH-1.10: black box replay index not implemented", strict=True)
def test_tc_e2e_010_blackbox_replay_index_available() -> None:
    out = subprocess.check_output(["bash", "-lc", "ls /tmp | grep blackbox_index"], text=True)
    assert out.strip() != ""
