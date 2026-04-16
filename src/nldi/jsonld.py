# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""JSON-LD builder for linked data feature responses.

Pure Python — no template engine. Converts feature properties and geometry
into a JSON-LD graph using schema.org, hydrologic features, and geosparql
vocabularies.
"""

import json as _json
from collections.abc import Iterator

JSONLD_CONTEXT = [
    {
        "schema": "https://schema.org/",
        "geo": "schema:geo",
        "hyf": "https://www.opengis.net/def/schema/hy_features/hyf/",
        "gsp": "http://www.opengis.net/ont/geosparql#",
        "name": "schema:name",
        "comid": {"@id": "schema:geoWithin", "@type": "@id"},
        "hyf:linearElement": {"@type": "@id"},
    }
]


def feature_to_jsonld(props: dict, geometry: dict | None = None) -> dict:
    """Convert feature properties and geometry to a JSON-LD entry."""
    entry: dict = {
        "@id": props.get("uri", ""),
        "@type": "https://www.opengis.net/def/schema/hy_features/hyf/HY_HydroLocation",
        "schema:subjectOf": {
            "@type": "schema:CreativeWork",
            "schema:identifier": props.get("source", ""),
            "schema:name": props.get("sourceName", ""),
        },
        "name": props.get("name", ""),
    }

    comid = props.get("comid")
    if comid:
        entry["comid"] = f"https://geoconnex.us/nhdplusv2/comid/{comid}"

    # Referenced position: mainstem and/or measure+reachcode
    positions = []
    mainstem = props.get("mainstem")
    if mainstem:
        positions.append({"hyf:HY_IndirectPosition": {"hyf:linearElement": mainstem}})

    measure = props.get("measure")
    reachcode = props.get("reachcode")
    if measure and reachcode:
        positions.append(
            {
                "hyf:HY_IndirectPosition": {
                    "hyf:distanceExpression": {"hyf:HY_IndirectPosition": {"hyf:interpolative": measure}},
                    "hyf:distanceDescription": {"hyf:HY_DistanceDescription": "upstream"},
                    "hyf:HY_IndirectPosition": {
                        "hyf:linearElement": f"https://geoconnex.us/nhdplusv2/reachcode/{reachcode}"
                    },
                }
            }
        )
    entry["hyf:referencedPosition"] = positions

    # Geometry — only for Point
    if geometry and geometry.get("type") == "Point":
        coords = geometry.get("coordinates", [])
        if len(coords) >= 2:
            lon, lat = coords[0], coords[1]
            entry["geo"] = {
                "@type": "schema:GeoCoordinates",
                "schema:longitude": lon,
                "schema:latitude": lat,
            }
            entry["gsp:hasGeometry"] = {
                "@type": "http://www.opengis.net/ont/sf#Point",
                "gsp:asWKT": {
                    "@value": f"POINT({lon} {lat})",
                    "@type": "http://www.opengis.net/ont/geosparql#wktLiteral",
                },
            }

    return entry


def to_jsonld_graph(features: list[dict]) -> dict:
    """Wrap multiple features in a JSON-LD @graph."""
    entries = [feature_to_jsonld(f.get("properties", {}), f.get("geometry")) for f in features]
    return {"@context": JSONLD_CONTEXT, "@id": "_:graph", "@graph": entries}


def to_jsonld_single(feature: dict) -> dict:
    """Convert a single feature to a root-level JSON-LD document."""
    entry = feature_to_jsonld(feature.get("properties", {}), feature.get("geometry"))
    return {"@context": JSONLD_CONTEXT, **entry}


def stream_jsonld_graph(features: list[dict]) -> Iterator[bytes]:
    """Yield a JSON-LD @graph incrementally.

    The DB query is complete before this is called — no connection is held
    during streaming.
    """
    header = _json.dumps({"@context": JSONLD_CONTEXT, "@id": "_:graph", "@graph": []})
    yield header[:-2].encode()  # strip trailing `]}`
    for i, feat in enumerate(features):
        if i > 0:
            yield b","
        yield _json.dumps(feature_to_jsonld(feat.get("properties", {}), feat.get("geometry"))).encode()
    yield b"]}"
