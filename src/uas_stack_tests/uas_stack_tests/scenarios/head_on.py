"""Head-on: tráfico opuesto en eje N."""

from __future__ import annotations

from flightmind_msgs.msg import TrafficIntruder

from uas_stack_tests.scenario_lib import OwnshipKinematic, run_scenario_node


def _own(_t: float) -> OwnshipKinematic:
    return OwnshipKinematic(0.0, 0.0, -80.0, 40.0, 0.0, 0.0)


def _intr(_t: float) -> TrafficIntruder:
    m = TrafficIntruder()
    m.id = 101
    m.n_m = 1400.0
    m.e_m = 0.0
    m.z_ned_m = -80.0
    m.vn_mps = -38.0
    m.ve_mps = 0.0
    m.vd_mps = 0.0
    return m


def main() -> None:
    run_scenario_node(
        scenario_name="scenario_head_on",
        ownship_fn=_own,
        intruder_fn=_intr,
        duration_s=14.0,
    )


if __name__ == "__main__":
    main()
