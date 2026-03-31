# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Data Transfer Objects — the message model layer.

DTOs define the shape of API responses, separate from ORM models.
See docs/principles.md #2: "Separate the models" (Amundsen's Maxim).
"""

import msgspec


class DataSource(msgspec.Struct):
    """A data source in the NLDI source registry."""

    source: str
    sourceName: str  # noqa: N815
    features: str
