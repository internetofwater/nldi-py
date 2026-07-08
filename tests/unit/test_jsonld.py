"""Unit tests for JSON-LD builder."""

from nldi.jsonld import JSONLD_CONTEXT, feature_to_jsonld, to_jsonld_graph, to_jsonld_single


def test_feature_to_jsonld_full():
    props = {
        "uri": "https://example.com/feature/1",
        "source": "wqp",
        "sourceName": "Water Quality Portal",
        "name": "Test Site",
        "comid": 13294176,
        "mainstem": "https://geoconnex.us/ref/mainstems/123",
        "measure": 50.5,
        "reachcode": "07090002008384",
    }
    geom = {"type": "Point", "coordinates": [-89.44, 43.14]}
    result = feature_to_jsonld(props, geom)

    assert result["@id"] == "https://example.com/feature/1"
    assert result["@type"] == "https://www.opengis.net/def/schema/hy_features/hyf/HY_HydroLocation"
    assert result["schema:subjectOf"]["schema:identifier"] == "wqp"
    assert result["name"] == "Test Site"
    assert result["comid"] == "https://geoconnex.us/nhdplusv2/comid/13294176"
    assert len(result["hyf:referencedPosition"]) == 2
    assert result["geo"]["schema:longitude"] == -89.44
    assert "gsp:hasGeometry" in result


def test_feature_to_jsonld_missing_optional_fields():
    props = {"uri": "", "source": "wqp", "sourceName": "WQP", "name": ""}
    result = feature_to_jsonld(props, None)

    assert "comid" not in result
    assert result["hyf:referencedPosition"] == []
    assert "geo" not in result
    assert "gsp:hasGeometry" not in result


def test_feature_to_jsonld_no_geometry():
    props = {"uri": "", "source": "wqp", "sourceName": "WQP", "name": "", "comid": 123}
    result = feature_to_jsonld(props, {"type": "LineString", "coordinates": []})

    # LineString geometry should not produce geo/gsp entries
    assert "geo" not in result


def test_to_jsonld_graph():
    features = [
        {"properties": {"uri": "a", "source": "wqp", "sourceName": "WQP", "name": "A"}, "geometry": None},
        {"properties": {"uri": "b", "source": "wqp", "sourceName": "WQP", "name": "B"}, "geometry": None},
    ]
    result = to_jsonld_graph(features)

    assert result["@context"] == JSONLD_CONTEXT
    assert result["@id"] == "_:graph"
    assert len(result["@graph"]) == 2


def test_to_jsonld_single():
    feature = {"properties": {"uri": "https://example.com/1", "source": "wqp", "sourceName": "WQP", "name": "X"}, "geometry": None}
    result = to_jsonld_single(feature)

    assert result["@context"] == JSONLD_CONTEXT
    assert result["@id"] == "https://example.com/1"
    assert "@graph" not in result
