"""Parity test fixtures and helpers."""

import json
import os
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
PY_BASE = os.getenv("NLDI_TEST_URL", "http://localhost:8000/api/nldi")
JAVA_BASE = "https://api.water.usgs.gov/nldi"


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=PY_BASE + "/", timeout=30) as c:
        yield c


def load_fixture(name: str) -> dict | list:
    return json.loads((FIXTURES / name).read_text())


def strip_geometry(obj):
    """Recursively null out geometry fields."""
    if isinstance(obj, dict):
        return {k: (None if k == "geometry" else strip_geometry(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strip_geometry(item) for item in obj]
    return obj


def normalize_urls(obj, old_base: str, new_base: str):
    """Recursively replace base URL strings."""
    if isinstance(obj, str):
        return obj.replace(old_base, new_base)
    if isinstance(obj, dict):
        return {k: normalize_urls(v, old_base, new_base) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_urls(item, old_base, new_base) for item in obj]
    return obj


def normalize_comid(obj):
    """Recursively convert comid values to string for comparison."""
    if isinstance(obj, dict):
        return {
            k: (str(v) if k == "comid" and v is not None else normalize_comid(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [normalize_comid(item) for item in obj]
    return obj


def summarize_collection(body: dict) -> dict:
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
    return {
        "feature_count": len(features),
        "property_keys": sorted(all_keys),
        "geometry_types": sorted(geom_types),
        "sources_present": sorted(sources),
    }
