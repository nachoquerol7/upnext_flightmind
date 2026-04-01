"""Fase 9: launch, métricas, matriz V&V, sintaxis de scripts."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

from uas_stack_tests.scenario_lib import OwnshipKinematic, estimate_miss_distance_m, ra_type_label


def _src_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_full_stack_launch_registers_all_stack_nodes() -> None:
    launch_py = _src_root() / "launch" / "full_stack.launch.py"
    assert launch_py.is_file()
    spec = importlib.util.spec_from_file_location("uas_full_stack_launch", launch_py)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ld = mod.generate_launch_description()
    assert len(ld.entities) >= 11


def test_vv_matrix_has_seven_requirement_rows() -> None:
    md = _src_root() / "docs" / "VV_MATRIX.md"
    text = md.read_text(encoding="utf-8")
    assert "| R-VM-01 |" in text
    assert "| R-INT-01 |" in text
    assert text.count("| R-") >= 7


def test_estimate_miss_distance_parallel_tracks() -> None:
    own = OwnshipKinematic(0.0, 0.0, 0.0, 40.0, 0.0, 0.0)
    intr = OwnshipKinematic(0.0, 200.0, 0.0, 40.0, 0.0, 0.0)
    d = estimate_miss_distance_m(own, intr, horizon_s=30.0)
    assert abs(d - 200.0) < 1.0


def test_ra_type_label_mapping() -> None:
    assert ra_type_label(0.0, 0.0, False) == "NONE"
    assert ra_type_label(2.0, 0.0, True) == "CLIMB"
    assert ra_type_label(-2.0, 0.0, True) == "DESCEND"


@pytest.mark.parametrize(
    "name",
    [
        "scripts/scenario_head_on.py",
        "scripts/scenario_overtake.py",
        "scripts/scenario_crossing.py",
        "scripts/scenario_geofence.py",
        "scripts/daa_dashboard.py",
        "uas_stack_tests/dashboard.py",
        "uas_stack_tests/scenario_lib.py",
    ],
)
def test_python_files_parse(name: str) -> None:
    p = _src_root() / name
    ast.parse(p.read_text(encoding="utf-8"), filename=str(p))


def test_scenario_modules_importable() -> None:
    import uas_stack_tests.scenarios.head_on  # noqa: F401
    import uas_stack_tests.scenarios.overtake  # noqa: F401
    import uas_stack_tests.scenarios.crossing  # noqa: F401
    import uas_stack_tests.scenarios.geofence  # noqa: F401
