"""Unit tests for utilities."""

import pytest

from nldi.util import parse_wkt_point


def test_parse_valid_point():
    lon, lat = parse_wkt_point("POINT(-89.509 43.087)")
    assert lon == -89.509
    assert lat == 43.087


def test_parse_point_with_spaces():
    lon, lat = parse_wkt_point("POINT( -89.509  43.087 )")
    assert lon == -89.509


def test_parse_invalid_raises():
    with pytest.raises(ValueError, match="Invalid WKT"):
        parse_wkt_point("NOT A POINT")
