# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Media type constants for the NLDI API."""

from enum import StrEnum


class MediaType(StrEnum):
    """Media types used by the NLDI API.

    Replicates relevant Litestar media types and adds API-specific ones,
    so we have a single source of truth independent of the framework.
    """

    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
    GEOJSON = "application/vnd.geo+json"
    JSONLD = "application/ld+json"
    PROBLEM_JSON = "application/problem+json"
