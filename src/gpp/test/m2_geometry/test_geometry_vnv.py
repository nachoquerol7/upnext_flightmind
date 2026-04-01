from __future__ import annotations

import json

import pytest

from gpp.geometry import parse_geofences_json, point_in_polygon, segment_hits_nfz


SQUARE = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]


def test_tc_geo_001_point_inside_square() -> None:
    assert point_in_polygon(50.0, 50.0, SQUARE)


def test_tc_geo_002_point_outside_square() -> None:
    assert not point_in_polygon(200.0, 200.0, SQUARE)


def test_tc_geo_003_point_on_border_document_current_behavior() -> None:
    result = point_in_polygon(0.0, 50.0, SQUARE)
    assert isinstance(result, bool)


def test_tc_geo_004_concave_hole_like_point_is_outside() -> None:
    poly_l = [(0.0, 0.0), (100.0, 0.0), (100.0, 30.0), (30.0, 30.0), (30.0, 100.0), (0.0, 100.0)]
    assert not point_in_polygon(60.0, 60.0, poly_l)


def test_tc_geo_005_polygon_with_two_vertices_is_false() -> None:
    assert not point_in_polygon(1.0, 1.0, [(0.0, 0.0), (1.0, 1.0)])


def test_tc_geo_006_segment_crosses_wall() -> None:
    wall = [(100.0, -10.0), (200.0, -10.0), (200.0, 10.0), (100.0, 10.0)]
    assert segment_hits_nfz(0.0, 0.0, 300.0, 0.0, [wall])


def test_tc_geo_007_segment_does_not_cross_nfz() -> None:
    wall = [(100.0, -10.0), (200.0, -10.0), (200.0, 10.0), (100.0, 10.0)]
    assert not segment_hits_nfz(0.0, 50.0, 300.0, 50.0, [wall])


def test_tc_geo_008_small_nfz_detected_by_adaptive_sampling() -> None:
    tiny = [(4999.5, -0.5), (5000.5, -0.5), (5000.5, 0.5), (4999.5, 0.5)]
    assert segment_hits_nfz(0.0, 0.0, 10000.0, 0.0, [tiny], min_step_m=0.5)


def test_tc_geo_009_parse_two_valid_polygons() -> None:
    js = json.dumps({"polygons": [SQUARE, [(0, 0), (1, 0), (0, 1)]]})
    polys = parse_geofences_json(js)
    assert len(polys) == 2


def test_tc_geo_010_parse_empty_inputs() -> None:
    assert parse_geofences_json("") == []
    assert parse_geofences_json("{}") == []


def test_tc_geo_011_ignore_invalid_two_vertex_polygon() -> None:
    js = json.dumps({"polygons": [[(0, 0), (1, 1)], [(0, 0), (1, 0), (0, 1)]]})
    polys = parse_geofences_json(js)
    assert len(polys) == 1


def test_tc_geo_012_malformed_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_geofences_json("{not-json")
