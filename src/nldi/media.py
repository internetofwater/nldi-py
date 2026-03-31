# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Media type constants for the NLDI API.

Follows IANA media type conventions. Each member carries a description
for self-documentation. Extend as needed — only include types we use.
"""

from enum import StrEnum


class MediaType(StrEnum):
    """IANA-registered media types used by the NLDI API."""

    def __new__(cls, value: str, description: str = ""):
        """Create a new MediaType with value and description."""
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj

    JSON = "application/json", "JSON format — RFC 8259"
    HTML = "text/html", "HTML document format"
    GEOJSON = "application/geo+json", "GeoJSON format — RFC 7946"
    JSONLD = "application/ld+json", "JSON-LD linked data format"
    PROBLEM_JSON = "application/problem+json", "RFC 9457 Problem Details for HTTP APIs"
    OPENAPI_JSON = (
        "application/vnd.oai.openapi+json;version=3.0",
        "OpenAPI 3.0 specification in JSON format",
    )
