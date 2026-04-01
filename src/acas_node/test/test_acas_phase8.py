"""Fase 8 ACAS Xu: tabla de amenaza + publicación condicional al FC."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from acas_node.acas_fc import emit_acas_outputs
from acas_node.acas_logic import (
    AcasConfig,
    AcasDecision,
    IntruderState,
    OwnshipState,
    compute_acas_decision,
)

_CFG = AcasConfig(
    tau_ca_s=60.0,
    dmod_ca_m=2500.0,
    z_sep_m=200.0,
    ra_climb_rate_mps=3.0,
    ra_heading_delta_deg=30.0,
)


def test_no_ra_when_traffic_clear() -> None:
    own = OwnshipState(0.0, 0.0, 0.0, 40.0, 0.0, 0.0)
    assert not compute_acas_decision(own, [], _CFG).ra_active
    far = IntruderState(1, 80_000.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert not compute_acas_decision(own, [far], _CFG).ra_active


def test_ra_climb_on_head_on() -> None:
    own = OwnshipState(0.0, 0.0, 0.0, 40.0, 0.0, 0.0)
    intr = IntruderState(2, 800.0, 0.0, 0.0, -40.0, 0.0, 0.0)
    d = compute_acas_decision(own, [intr], _CFG)
    assert d.ra_active
    assert d.threat_class == "HEAD_ON"
    assert d.climb_rate_mps > 0
    assert abs(d.heading_delta_deg - _CFG.ra_heading_delta_deg) < 1e-6


def test_ra_descend_on_overtake() -> None:
    own = OwnshipState(0.0, 0.0, 0.0, 40.0, 0.0, 0.0)
    intr = IntruderState(3, 600.0, 0.0, 0.0, 15.0, 0.0, 0.0)
    d = compute_acas_decision(own, [intr], _CFG)
    assert d.ra_active
    assert d.threat_class == "OVERTAKE"
    assert d.climb_rate_mps < 0
    assert d.heading_delta_deg == 0.0


@patch("acas_node.acas_fc.build_trajectory_setpoint")
def test_no_publish_to_fc_when_clear(mock_build: MagicMock) -> None:
    pub = MagicMock()
    own = OwnshipState(0.0, 0.0, 0.0, 40.0, 0.0, 0.0)
    emit_acas_outputs(pub, own, AcasDecision(False, 3.0, 30.0, ""), 123)
    pub.publish.assert_not_called()
    mock_build.assert_not_called()


@patch("acas_node.acas_fc.build_trajectory_setpoint")
def test_ra_clears_when_traffic_resolves(mock_build: MagicMock) -> None:
    own = OwnshipState(0.0, 0.0, 0.0, 40.0, 0.0, 0.0)
    intr = IntruderState(4, 800.0, 0.0, 0.0, -40.0, 0.0, 0.0)
    d1 = compute_acas_decision(own, [intr], _CFG)
    assert d1.ra_active
    d2 = compute_acas_decision(own, [], _CFG)
    assert not d2.ra_active
    pub = MagicMock()
    emit_acas_outputs(pub, own, d2, 1)
    pub.publish.assert_not_called()
    mock_build.assert_not_called()
