"""Unit tests for GeoJSON DTOs."""

import json

import msgspec


def test_feature_serializes():
    from nldi.geojson import Feature, Point

    f = Feature(
        geometry=Point(coordinates=(-89.509, 43.087)),
        properties={"name": "test", "source": "wqp"},
    )
    data = msgspec.json.encode(f)
    parsed = json.loads(data)
    assert parsed["type"] == "Feature"
    assert parsed["geometry"]["type"] == "Point"
    assert parsed["geometry"]["coordinates"] == [-89.509, 43.087]
    assert parsed["properties"]["name"] == "test"


def test_feature_collection_serializes():
    from nldi.geojson import Feature, FeatureCollection, Point

    fc = FeatureCollection(features=[
        Feature(geometry=Point(coordinates=(-89.0, 43.0)), properties={"id": "1"}),
        Feature(geometry=Point(coordinates=(-90.0, 44.0)), properties={"id": "2"}),
    ])
    data = msgspec.json.encode(fc)
    parsed = json.loads(data)
    assert parsed["type"] == "FeatureCollection"
    assert len(parsed["features"]) == 2


def test_linestring_feature():
    from nldi.geojson import Feature, LineString

    f = Feature(
        geometry=LineString(coordinates=[(-89.0, 43.0), (-89.1, 43.1)]),
        properties={"comid": "123"},
    )
    data = msgspec.json.encode(f)
    parsed = json.loads(data)
    assert parsed["geometry"]["type"] == "LineString"
    assert len(parsed["geometry"]["coordinates"]) == 2


def test_parse_geojson_point():
    from nldi.geojson import Point, parse_geometry

    geom = parse_geometry('{"type": "Point", "coordinates": [-89.509, 43.087]}')
    assert isinstance(geom, Point)
    assert geom.coordinates == (-89.509, 43.087)


def test_parse_geojson_linestring():
    from nldi.geojson import LineString, parse_geometry

    geom = parse_geometry('{"type": "LineString", "coordinates": [[-89.0, 43.0], [-89.1, 43.1]]}')
    assert isinstance(geom, LineString)
    assert len(geom.coordinates) == 2
