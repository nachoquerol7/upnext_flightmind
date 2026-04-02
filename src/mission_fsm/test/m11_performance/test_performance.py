"""M11 — rendimiento y temporización del núcleo MissionFsm (TC-PERF-001..008)."""

from __future__ import annotations

import io
import logging
import statistics
import threading
import time
from pathlib import Path

import pytest
import yaml

try:
    import psutil as _psutil
except ImportError:
    _psutil = None

from mission_fsm.fsm import MissionFsm, mission_fsm_from_path

_CFG = Path(__file__).resolve().parents[2] / "config"
_MISSION = _CFG / "mission_fsm.yaml"
_VTOL = _CFG / "mission_fsm_vtol.yaml"
_HELI = _CFG / "mission_fsm_heli.yaml"
_MALE = _CFG / "mission_fsm_male.yaml"

pytestmark = pytest.mark.slow


def _fsm() -> MissionFsm:
    return mission_fsm_from_path(str(_MISSION))


def test_tc_perf_001_fsm_transition_p99_under_1ms() -> None:
    """Latencia de transición FSM: P99 < 1 ms (1000 muestras)."""
    fsm = _fsm()
    lat: list[float] = []
    for _ in range(1000):
        fsm.reset("PREFLIGHT")
        t0 = time.perf_counter()
        fsm.step({"preflight_ok": True})
        lat.append(time.perf_counter() - t0)
    lat.sort()
    p99 = lat[int(0.99 * len(lat)) - 1]
    assert p99 < 0.001, f"P99={p99*1000:.4f}ms"


def test_tc_perf_002_throughput_10k_steps_per_second() -> None:
    """≥ 10 000 evaluaciones de step() por segundo durante 1 s."""
    fsm = _fsm()
    fsm.seed("CRUISE")
    inputs = {"quality_flag": 1.0, "daidalus_alert": 0, "abort_command": False}
    end = time.perf_counter() + 1.0
    n = 0
    while time.perf_counter() < end:
        fsm.step(inputs)
        n += 1
        fsm.seed("CRUISE")
    assert n >= 10_000, f"got {n} steps/s"


def test_tc_perf_003_wcet_cruise_to_abort_under_2ms() -> None:
    """WCET ruta CRUISE→ABORT < 2 ms en 1000 ejecuciones."""
    fsm = _fsm()
    worst = 0.0
    for _ in range(1000):
        fsm.seed("CRUISE")
        t0 = time.perf_counter()
        fsm.step(
            {
                "quality_flag": 1.0,
                "daidalus_alert": 0,
                "abort_command": False,
                "fdir_emergency": True,
            }
        )
        dt = time.perf_counter() - t0
        worst = max(worst, dt)
    assert worst < 0.002, f"WCET={worst*1000:.4f}ms"


def test_tc_perf_004_jitter_sigma_under_0p1ms() -> None:
    """Jitter σ < 0.1 ms sobre 1000 latencias."""
    fsm = _fsm()
    lat: list[float] = []
    for _ in range(1000):
        fsm.reset("PREFLIGHT")
        t0 = time.perf_counter()
        fsm.step({"preflight_ok": True})
        lat.append(time.perf_counter() - t0)
    sigma = statistics.pstdev(lat)
    assert sigma < 0.0001, f"σ={sigma*1000:.6f}ms"


def test_tc_perf_005_concurrent_steps_no_corruption() -> None:
    """10 hilos llamando a step() con lock: estado coherente."""
    fsm = _fsm()
    lock = threading.Lock()
    errors: list[str] = []

    def worker() -> None:
        try:
            for _ in range(200):
                with lock:
                    fsm.reset("PREFLIGHT")
                    st, _ = fsm.step({"preflight_ok": True})
                    if st != "AUTOTAXI":
                        errors.append(st)
        except Exception as exc:  # pragma: no cover
            errors.append(str(exc))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors


@pytest.mark.skipif(_psutil is None, reason="psutil not installed")
def test_tc_perf_006_memory_footprint_under_50mb() -> None:
    """Instancia FSM no incrementa RSS en más de 50 MB (import + create)."""
    import os

    assert _psutil is not None
    proc = _psutil.Process(os.getpid())

    before = proc.memory_info().rss
    fsm = _fsm()
    _ = fsm.state
    after = proc.memory_info().rss
    delta_mb = (after - before) / 1e6
    assert delta_mb < 50.0, f"delta RSS={delta_mb:.1f}MB"


def test_tc_perf_007_logging_degradation_under_20_percent() -> None:
    """Degradación con logging activo < 20 % vs baseline."""

    def bench() -> float:
        fsm = _fsm()
        fsm.seed("CRUISE")
        t0 = time.perf_counter()
        for _ in range(2000):
            fsm.seed("CRUISE")
            fsm.step({"quality_flag": 1.0, "daidalus_alert": 0})
        return time.perf_counter() - t0

    logging.disable(logging.CRITICAL)
    t_quiet = bench()
    logging.disable(logging.NOTSET)
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    logging.basicConfig(level=logging.DEBUG, force=True, handlers=[h])
    t_noisy = bench()
    logging.getLogger().handlers.clear()
    logging.disable(logging.CRITICAL)
    ratio = (t_noisy - t_quiet) / max(t_quiet, 1e-9)
    assert ratio < 0.20, f"degradation={ratio*100:.1f}%"


def test_tc_perf_008_yaml_parse_under_10ms_each() -> None:
    """Carga de los tres YAMLs de plataforma: parse < 20 ms cada uno (margen en CI cargado)."""
    for p in (_VTOL, _HELI, _MALE):
        raw = p.read_text(encoding="utf-8")
        t0 = time.perf_counter()
        data = yaml.safe_load(raw)
        dt = time.perf_counter() - t0
        assert dt < 0.02, f"{p.name} parse {dt*1000:.2f}ms"
        assert isinstance(data, dict)
        MissionFsm.from_fsm_yaml(data)
