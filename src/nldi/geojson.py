# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""GeoJSON data structures as msgspec structs.

Adapted from https://github.com/jcrist/msgspec/blob/main/examples/geojson/msgspec_geojson.py
(BSD 3-Clause License). These are the message model for all GeoJSON API responses.
"""

from __future__ import annotations

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
