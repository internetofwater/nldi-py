# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""GeoJSON data structures as msgspec structs.

Adapted from https://github.com/jcrist/msgspec/blob/main/examples/geojson/msgspec_geojson.py
(BSD 3-Clause License). These are the message model for all GeoJSON API responses.
"""

from __future__ import annotations

from collections.abc import Iterator

import msgspec

Position = tuple[float, float]


class Point(msgspec.Struct, tag=True):
    """GeoJSON Point geometry."""

    coordinates: Position


class MultiPoint(msgspec.Struct, tag=True):
    """GeoJSON MultiPoint geometry."""

    coordinates: list[Position]


class LineString(msgspec.Struct, tag=True):
    """GeoJSON LineString geometry."""

    coordinates: list[Position]


class MultiLineString(msgspec.Struct, tag=True):
    """GeoJSON MultiLineString geometry."""

    coordinates: list[list[Position]]


class Polygon(msgspec.Struct, tag=True):
    """GeoJSON Polygon geometry."""

    coordinates: list[list[Position]]


class MultiPolygon(msgspec.Struct, tag=True):
    """GeoJSON MultiPolygon geometry."""

    coordinates: list[list[list[Position]]]


class GeometryCollection(msgspec.Struct, tag=True):
    """GeoJSON GeometryCollection."""

    geometries: list[Geometry]


Geometry = Point | MultiPoint | LineString | MultiLineString | Polygon | MultiPolygon | GeometryCollection


class Feature(msgspec.Struct, tag=True):
    """GeoJSON Feature."""

    geometry: Geometry | None = None
    properties: dict | None = None
    id: str | int | None = None


class FeatureCollection(msgspec.Struct, tag=True):
    """GeoJSON FeatureCollection."""

    features: list[Feature]


_geometry_decoder = msgspec.json.Decoder(Geometry)


def parse_geometry(geojson_str: str) -> Geometry:
    """Parse a GeoJSON geometry string (from ST_AsGeoJSON) into a Geometry struct."""
    return _geometry_decoder.decode(geojson_str)


def stream_feature_collection(features: list[Feature]) -> Iterator[bytes]:
    """Yield a GeoJSON FeatureCollection incrementally.

    The DB query is complete before this is called — no connection is held
    during streaming. A client hangup mid-stream has no effect on the pool.
    """
    yield b'{"type":"FeatureCollection","features":['
    for i, feat in enumerate(features):
        if i > 0:
            yield b","
        yield msgspec.json.encode(feat)
    yield b"]}"
