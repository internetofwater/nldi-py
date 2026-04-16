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


def test_stream_feature_collection_empty():
    from nldi.geojson import stream_feature_collection

    result = json.loads(b"".join(stream_feature_collection([])))
    assert result == {"type": "FeatureCollection", "features": []}


def test_stream_feature_collection_single():
    from nldi.geojson import Feature, Point, stream_feature_collection

    features = [Feature(geometry=Point(coordinates=(-89.0, 43.0)), properties={"id": "1"})]
    result = json.loads(b"".join(stream_feature_collection(features)))
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1


def test_stream_feature_collection_multiple():
    from nldi.geojson import Feature, Point, stream_feature_collection

    features = [Feature(geometry=Point(coordinates=(-89.0 - i, 43.0)), properties={"id": str(i)}) for i in range(5)]
    result = json.loads(b"".join(stream_feature_collection(features)))
    assert len(result["features"]) == 5
