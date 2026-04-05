# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Small utilities — no heavy dependencies."""

import re

_WKT_POINT_RE = re.compile(r"POINT\s*\(\s*([+-]?\d+\.?\d*)\s+([+-]?\d+\.?\d*)\s*\)", re.IGNORECASE)


def parse_wkt_point(wkt: str) -> tuple[float, float]:
    """Parse a WKT POINT string to (lon, lat). No shapely needed."""
    m = _WKT_POINT_RE.match(wkt.strip())
    if not m:
        raise ValueError(f"Invalid WKT point: {wkt}")
    return float(m.group(1)), float(m.group(2))
