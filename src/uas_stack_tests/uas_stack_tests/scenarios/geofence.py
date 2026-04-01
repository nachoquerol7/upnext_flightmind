"""Geocerca: vuelo hacia polígono NFZ (PolyCARP + métricas en CSV)."""

from __future__ import annotations

import json

from flightmind_msgs.msg import TrafficIntruder

from uas_stack_tests.scenario_lib import OwnshipKinematic, run_scenario_node

_GF = {
    "polygons": [
        [[3200.0, -500.0], [3800.0, -500.0], [3800.0, 500.0], [3200.0, 500.0]],
    ]
}
_GF_STR = json.dumps(_GF)


def _own(_t: float) -> OwnshipKinematic:
    return OwnshipKinematic(2200.0, 0.0, -70.0, 32.0, 0.0, 0.0)


def _intr(_t: float) -> TrafficIntruder:
    m = TrafficIntruder()
    m.id = 999
    m.n_m = -50_000.0
    m.e_m = 0.0
    m.z_ned_m = 0.0
    m.vn_mps = 0.0
    m.ve_mps = 0.0
    m.vd_mps = 0.0
    return m


def _geo(_t: float) -> str:
    return _GF_STR


def main() -> None:
    run_scenario_node(
        scenario_name="scenario_geofence",
        ownship_fn=_own,
        intruder_fn=_intr,
        duration_s=16.0,
        geofence_json_fn=_geo,
    )


if __name__ == "__main__":
    main()
