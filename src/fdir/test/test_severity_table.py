"""TC-FDIR-S01..S03 — severity YAML load and lookup."""

from __future__ import annotations

import os

import pytest

from fdir.severity_table import load_severity_table, lookup_fault


def _severity_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "fdir_severity.yaml")
    )


def test_tc_fdir_s01_load_yaml() -> None:
    table = load_severity_table(_severity_path())
    assert isinstance(table, dict)
    assert "IMU_FAILED" in table


def test_tc_fdir_s02_imu_failed_mapping() -> None:
    table = load_severity_table(_severity_path())
    row = table["IMU_FAILED"]
    assert row["severity"] == "CRITICAL"
    assert row["action"] == "ABORT"


def test_tc_fdir_s03_lookup_fault() -> None:
    table = load_severity_table(_severity_path())
    row = lookup_fault(table, "BATTERY_LOW")
    assert row["action"] == "RTB"


def test_lookup_unknown_raises() -> None:
    table = load_severity_table(_severity_path())
    with pytest.raises(KeyError):
        lookup_fault(table, "NOT_A_FAULT")
