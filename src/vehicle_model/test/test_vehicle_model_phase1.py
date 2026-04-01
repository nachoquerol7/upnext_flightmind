"""Fase 1 — VehicleModel envelope tests."""

from vehicle_model.model import TrajectorySegment, VehicleModel


def test_vmin_increases_with_fuel_burn() -> None:
    m = VehicleModel(
        v_min_ms=30.0,
        v_max_ms=57.0,
        turn_radius_min_m=600.0,
        climb_rate_max_ms=8.0,
        descent_rate_max_ms=5.0,
        glide_ratio=18.0,
        mtow_kg=750.0,
        fuel_burn_kgh=50.0,
        fuel_mass_initial_kg=120.0,
        v_min_reserve_gain_ms=5.0,
    )
    m.update_weight(0.0)
    v0 = m.v_min_ms
    # Burn ~half the tank in 1.2 h at 50 kg/h → 60 kg burned → empty reserve policy kicks in
    m.update_weight(1.2)
    v1 = m.v_min_ms
    assert v1 > v0, "v_min should rise as fuel reserve drops"


def test_turn_radius_at_cruise_speed() -> None:
    m = VehicleModel(
        v_min_ms=30.0,
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
    r = m.turn_radius_at_cruise_speed()
    assert r == 600.0
    # At cruise speed with published turn radius, segment is feasible
    ok = m.is_feasible(
        [TrajectorySegment(speed_mps=m.v_max_ms, climb_rate_mps=0.0, turn_radius_m=600.0)]
    )
    assert ok is True


def test_feasibility_check_rejects_steep_climb() -> None:
    m = VehicleModel(
        v_min_ms=30.0,
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
    m.update_weight(0.0)
    bad = m.is_feasible(
        [
            TrajectorySegment(speed_mps=40.0, climb_rate_mps=25.0, turn_radius_m=float("inf")),
        ]
    )
    assert bad is False
    good = m.is_feasible(
        [
            TrajectorySegment(speed_mps=40.0, climb_rate_mps=7.0, turn_radius_m=float("inf")),
        ]
    )
    assert good is True
