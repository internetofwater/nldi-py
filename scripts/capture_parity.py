#!/usr/bin/env python
"""Capture golden files from the production Java NLDI service.

Fetches responses from the Java service, processes them into golden files
for parity testing. Two tiers:

  Tier 1 (full): Small responses stored complete with geometry nulled out.
  Tier 2 (summary): Large collections stored as a summary dict with
    feature count, property keys, geometry types, and one example feature.

Usage:
    uv run python scripts/capture_parity.py

Re-run when the Java service changes or the DB is re-crawled.
Golden files are written to tests/parity/fixtures/.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

JAVA_BASE = "https://api.water.usgs.gov/nldi"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "parity" / "fixtures"

# ---------------------------------------------------------------------------
# Tier 1: Full golden files (geometry stripped)
# Small responses where we store the complete JSON minus geometry coordinates.
# ---------------------------------------------------------------------------
TIER1_ENDPOINTS = {
    # Source list — small JSON array, no geometry
    "sources.json": "/linked-data?f=json",
    # Single feature by source+id
    "single_feature_wqp.json": "/linked-data/wqp/USGS-05427930?f=json",
    # Single feature by comid
    "single_feature_comid.json": "/linked-data/comid/13293396?f=json",
    # Navigation modes — small JSON object
    "nav_modes.json": "/linked-data/comid/13293396/navigation?f=json",
    # Single feature JSON-LD
    "single_feature_jsonld.json": "/linked-data/wqp/USGS-05427930?f=jsonld",
}

# ---------------------------------------------------------------------------
# Tier 2: Summary golden files
# Large collections where we store metadata + one example feature.
# ---------------------------------------------------------------------------
TIER2_ENDPOINTS = {
    # Features by source — nwissite is smaller than wqp
    "features_by_source.json": "/linked-data/nwissite?f=json",
    # Navigation flowlines — many LineString geometries
    "nav_dm_flowlines.json": "/linked-data/comid/13293396/navigation/DM/flowlines?distance=10&f=json",
    # Navigation features — many Point features
    "nav_dm_features_wqp.json": "/linked-data/comid/13293396/navigation/DM/wqp?distance=50&f=json",
    # Upstream navigation flowlines
    "nav_um_flowlines.json": "/linked-data/comid/13293396/navigation/UM/flowlines?distance=10&f=json",
}


def strip_geometry(obj):
    """Recursively null out geometry fields in a parsed JSON object."""
    if isinstance(obj, dict):
        return {
            k: (None if k == "geometry" else strip_geometry(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [strip_geometry(item) for item in obj]
    return obj


def summarize_collection(body, endpoint):
    """Build a tier 2 summary from a FeatureCollection response."""
    features = body.get("features", [])
    all_keys = set()
    geom_types = set()
    sources = set()
    for f in features:
        props = f.get("properties", {})
        all_keys.update(props.keys())
        if f.get("geometry"):
            geom_types.add(f["geometry"].get("type"))
        if "source" in props:
            sources.add(props["source"])

    first = None
    if features:
        first = strip_geometry(features[0])

    return {
        "endpoint": endpoint,
        "captured": datetime.now(timezone.utc).isoformat(),
        "feature_count": len(features),
        "content_type": "application/geo+json",
        "property_keys": sorted(all_keys),
        "geometry_types": sorted(geom_types),
        "sources_present": sorted(sources),
        "first_feature": first,
    }


def fetch(endpoint):
    """Fetch an endpoint from the Java service."""
    url = f"{JAVA_BASE}{endpoint}"
    print(f"  Fetching {url}")
    r = httpx.get(url, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def write_fixture(name, data):
    """Write a fixture file as formatted JSON."""
    path = FIXTURES / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"  Wrote {path}")


def main():
    FIXTURES.mkdir(parents=True, exist_ok=True)

    print("Tier 1: Full golden files (geometry stripped)")
    for name, endpoint in TIER1_ENDPOINTS.items():
        body = fetch(endpoint)
        write_fixture(name, strip_geometry(body))

    print("\nTier 2: Summary golden files")
    for name, endpoint in TIER2_ENDPOINTS.items():
        body = fetch(endpoint)
        write_fixture(name, summarize_collection(body, endpoint))

    print(f"\nDone. {len(TIER1_ENDPOINTS) + len(TIER2_ENDPOINTS)} fixtures written.")


if __name__ == "__main__":
    sys.exit(main() or 0)
