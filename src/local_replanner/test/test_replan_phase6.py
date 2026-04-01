"""Phase 6 local replanner tests."""

from __future__ import annotations

from local_replanner.replan_core import (
    clamp_fl_delta_by_climb_rate,
    delta_fl_for_quality,
    daidalus_advisory_feasible,
    replan_cost,
    margen_terreno_effective,
    emergency_waypoint_ne,
)
from local_replanner.trigger_monitor import TriggerSnapshot, select_active_trigger
from vehicle_model.model import VehicleModel


def test_cost_increases_with_low_quality_flag() -> None:
    fl, terrain = 40.0, 800.0
    m_hi = margen_terreno_effective(fl, terrain, 0.9)
    m_lo = margen_terreno_effective(fl, terrain, 0.45)
    c_hi = replan_cost(m_hi, 2000.0, 0.0, 1.0, 1.0, 0.5)
    c_lo = replan_cost(m_lo, 2000.0, 0.0, 1.0, 1.0, 0.5)
    assert c_lo > c_hi


def test_fl_adjusts_up_on_quality_flag_drop() -> None:
    base = 35.0
    d = delta_fl_for_quality(0.4)
    assert d >= 5.0
    capped = clamp_fl_delta_by_climb_rate(base, base + d, 8.0, 0.5)
    max_step = 8.0 * 0.5 / (100 * 0.3048)
    assert base < capped <= base + max_step + 1e-6


def test_daidalus_advisory_filtered_by_vehicle_model() -> None:
    vm = VehicleModel(
        v_min_ms=28.0,
        v_max_ms=57.0,
        turn_radius_min_m=600.0,
        climb_rate_max_ms=8.0,
        descent_rate_max_ms=5.0,
        glide_ratio=18.0,
        mtow_kg=750.0,
        fuel_burn_kgh=50.0,
        fuel_mass_initial_kg=100.0,
        v_min_reserve_gain_ms=0.0,
    )
    vm.update_weight(0.0)
    assert daidalus_advisory_feasible(vm, 40.0, 5.0) is True
    assert daidalus_advisory_feasible(vm, 40.0, 25.0) is False


def test_geofence_trigger_activates_replan() -> None:
    snap = TriggerSnapshot(
        emergency_json="",
        daidalus_alert=0,
        violation_imminent=True,
        quality_flag=0.9,
        qf_threshold=0.65,
        track_deviation_m=0.0,
        track_threshold_m=80.0,
    )
    assert select_active_trigger(snap) == "GEOFENCE"


def test_emergency_target_overrides_path() -> None:
    snap = TriggerSnapshot(
        emergency_json='{"reachable":true,"lat":40.05,"lon":-3.02,"n_m":5000,"e_m":1200}',
        daidalus_alert=2,
        violation_imminent=True,
        quality_flag=0.3,
        qf_threshold=0.65,
        track_deviation_m=500.0,
        track_threshold_m=80.0,
    )
    assert select_active_trigger(snap) == "EMERGENCY"


def test_multiple_triggers_priority_order() -> None:
    snap = TriggerSnapshot(
        emergency_json='{"reachable":true,"lat":40.0,"lon":-3.0}',
        daidalus_alert=2,
        violation_imminent=True,
        quality_flag=0.2,
        qf_threshold=0.65,
        track_deviation_m=500.0,
        track_threshold_m=80.0,
    )
    assert select_active_trigger(snap) == "EMERGENCY"


def test_no_replan_when_nominal() -> None:
    snap = TriggerSnapshot(
        emergency_json="",
        daidalus_alert=0,
        violation_imminent=False,
        quality_flag=0.95,
        qf_threshold=0.65,
        track_deviation_m=10.0,
        track_threshold_m=80.0,
    )
    assert select_active_trigger(snap) is None


def test_emergency_waypoint_prefers_n_m_e_m() -> None:
    d = {"reachable": True, "lat": 0.0, "lon": 0.0, "n_m": 1234.0, "e_m": 567.0}
    n, e = emergency_waypoint_ne(d, 0.0, 0.0)
    assert n == 1234.0 and e == 567.0
