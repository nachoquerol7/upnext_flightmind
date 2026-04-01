"""Overtaking: mismo rumbo, propio más rápido."""

from __future__ import annotations

from flightmind_msgs.msg import TrafficIntruder

from uas_stack_tests.scenario_lib import OwnshipKinematic, run_scenario_node


def _own(_t: float) -> OwnshipKinematic:
    return OwnshipKinematic(0.0, 0.0, -100.0, 42.0, 0.0, 0.0)


def _intr(_t: float) -> TrafficIntruder:
    m = TrafficIntruder()
    m.id = 102
    m.n_m = 900.0
    m.e_m = 0.0
    m.z_ned_m = -100.0
    m.vn_mps = 12.0
    m.ve_mps = 0.0
    m.vd_mps = 0.0
    return m


def main() -> None:
    run_scenario_node(
        scenario_name="scenario_overtake",
        ownship_fn=_own,
        intruder_fn=_intr,
        duration_s=14.0,
    )


if __name__ == "__main__":
    main()
