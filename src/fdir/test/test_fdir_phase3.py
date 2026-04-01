"""FDIR Phase 3 — one test per detector / policy / zone helper."""

from __future__ import annotations

import json
import os

from fdir.fdir_core import FdirConfig, FdirEngine, FdirSnapshot, config_from_yaml_root, load_fdir_yaml


def _cfg() -> FdirConfig:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "fdir.yaml"))
    return config_from_yaml_root(load_fdir_yaml(path))


def _snap(
    *,
    t: float,
    q: float | None = 0.9,
    last_q_rx: float | None = None,
    last_c2: float | None = None,
    thr: float = 0.0,
    vacc: float = 0.0,
    armed: bool = False,
    motor_px4: bool = False,
    lat: float = 40.0,
    lon: float = -3.0,
    alt: float = 2000.0,
) -> FdirSnapshot:
    lq = last_q_rx if last_q_rx is not None else t
    return FdirSnapshot(
        time_sec=t,
        quality_flag=q,
        last_quality_rx_time=lq,
        c2_heartbeat_last_rx=last_c2,
        throttle_commanded=thr,
        vertical_accel_m_s2=vacc,
        armed=armed,
        failure_motor_px4=motor_px4,
        fsm_mode="CRUISE",
        vehicle_lat=lat,
        vehicle_lon=lon,
        vehicle_altitude_amsl_m=alt,
    )


def test_nav_degraded_mild_policy() -> None:
    eng = FdirEngine(_cfg())
    out = eng.evaluate(_snap(t=10.0, q=0.5))
    assert out.active_fault == "NAV_DEGRADED"
    assert out.policy_action == "WIDEN_MARGINS_REDUCE_SPEED"


def test_nav_degraded_severe_triggers_hold() -> None:
    eng = FdirEngine(_cfg())
    out = eng.evaluate(_snap(t=10.0, q=0.25))
    assert out.active_fault == "NAV_DEGRADED"
    assert out.policy_action == "HOLD"


def test_nav_degraded_critical_triggers_rtb() -> None:
    eng = FdirEngine(_cfg())
    out = eng.evaluate(_snap(t=10.0, q=0.05))
    assert out.active_fault == "NAV_DEGRADED"
    assert out.policy_action == "RTB"


def test_motor_loss_triggers_emergency_lookup() -> None:
    eng = FdirEngine(_cfg())
    out = eng.evaluate(
        _snap(t=10.0, q=0.9, last_c2=10.0, armed=True, motor_px4=True, lat=40.0, lon=-3.0, alt=2000.0)
    )
    assert out.active_fault == "MOTOR_LOSS"
    assert out.policy_action == "GLIDE_EMERGENCY_TARGET"
    data = json.loads(out.emergency_landing_target_json)
    assert data.get("reachable") is True
    assert "lat" in data and "lon" in data


def test_link_loss_30s_triggers_rtb() -> None:
    eng = FdirEngine(_cfg())
    out = eng.evaluate(_snap(t=100.0, q=0.9, last_q_rx=100.0, last_c2=69.0))
    assert out.active_fault == "LINK_LOSS"
    assert out.policy_action == "RTB"


def test_link_loss_120s_triggers_land() -> None:
    eng = FdirEngine(_cfg())
    out = eng.evaluate(_snap(t=200.0, q=0.9, last_q_rx=200.0, last_c2=75.0))
    assert out.active_fault == "LINK_LOSS"
    assert out.policy_action == "LAND_BEST_AVAILABLE"
    data = json.loads(out.emergency_landing_target_json)
    assert "reachable" in data


def test_sensor_timeout_triggers_hold() -> None:
    eng = FdirEngine(_cfg())
    out = eng.evaluate(_snap(t=50.0, q=0.9, last_q_rx=40.0))
    assert out.active_fault == "SENSOR_TIMEOUT"
    assert out.policy_action == "HOLD"


def test_emergency_zone_reachable_from_altitude() -> None:
    eng = FdirEngine(_cfg())
    snap = _snap(t=1.0, q=0.9, last_c2=1.0, lat=40.0, lon=-3.0, alt=3000.0)
    z = eng.pick_emergency_zone(snap)
    assert z is not None
    assert z["reachable"] is True
    assert z["distance_m"] < z["glide_distance_available_m"]


def test_emergency_zone_unreachable_filtered() -> None:
    cfg = _cfg()
    cfg.glide_ratio = 5.0
    eng = FdirEngine(cfg)
    snap = _snap(t=1.0, q=0.9, last_c2=1.0, lat=0.0, lon=0.0, alt=50.0)
    assert eng.pick_emergency_zone(snap) is None
