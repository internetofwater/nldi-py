"""Parity tests — compare Python NLDI responses against Java golden files.

Run with: task test:parity
Requires a running app (task dev) pointed at real RDS + pygeoapi.
"""

import pytest

from .conftest import (
    JAVA_BASE,
    PY_BASE,
    load_fixture,
    normalize_urls,
    strip_geometry,
    summarize_collection,
)

pytestmark = pytest.mark.parity


# ---------------------------------------------------------------------------
# Tier 1: Full comparison (geometry stripped, URLs normalized)
# ---------------------------------------------------------------------------


class TestSourceList:
    def test_sources_match(self, client):
        """Source list structure matches Java."""
        golden = load_fixture("sources.json")
        r = client.get("linked-data?f=json")
        actual = r.json()

        # Normalize URLs so base differences don't matter
        golden_norm = normalize_urls(golden, JAVA_BASE, PY_BASE)

        # Sort both by source name for stable comparison
        golden_sorted = sorted(golden_norm, key=lambda s: s["source"])
        actual_sorted = sorted(actual, key=lambda s: s["source"])

        # Compare keys and source names — feature URLs will differ by base only
        golden_sources = {s["source"] for s in golden_sorted}
        actual_sources = {s["source"] for s in actual_sorted}
        assert golden_sources == actual_sources, f"Missing: {golden_sources - actual_sources}, Extra: {actual_sources - golden_sources}"


class TestSingleFeature:
    def test_wqp_feature_structure(self, client):
        """Single WQP feature has same property keys as Java."""
        golden = load_fixture("single_feature_wqp.json")
        r = client.get("linked-data/wqp/USGS-05427930?f=json")
        actual = strip_geometry(r.json())

        golden_keys = set(golden["features"][0]["properties"].keys())
        actual_keys = set(actual["features"][0]["properties"].keys())
        assert golden_keys == actual_keys

    def test_comid_feature_structure(self, client):
        """Single comid feature has same property keys as Java."""
        golden = load_fixture("single_feature_comid.json")
        r = client.get("linked-data/comid/13293396?f=json")
        actual = strip_geometry(r.json())

        golden_keys = set(golden["features"][0]["properties"].keys())
        actual_keys = set(actual["features"][0]["properties"].keys())
        assert golden_keys == actual_keys

    def test_wqp_feature_values(self, client):
        """Key property values match Java for a known feature."""
        golden = load_fixture("single_feature_wqp.json")
        r = client.get("linked-data/wqp/USGS-05427930?f=json")

        gp = golden["features"][0]["properties"]
        ap = r.json()["features"][0]["properties"]

        assert ap["identifier"] == gp["identifier"]
        assert ap["name"] == gp["name"]
        assert ap["source"] == gp["source"]
        assert ap["sourceName"] == gp["sourceName"]
        assert str(ap["comid"]) == str(gp["comid"])


class TestNavModes:
    def test_nav_modes_match(self, client):
        """Navigation modes response matches Java structure."""
        golden = load_fixture("nav_modes.json")
        r = client.get("linked-data/comid/13293396/navigation?f=json")
        actual = r.json()

        golden_norm = normalize_urls(golden, JAVA_BASE, PY_BASE)
        assert set(golden_norm.keys()) == set(actual.keys())


class TestJsonLd:
    def test_jsonld_context_matches(self, client):
        """JSON-LD @context matches Java."""
        golden = load_fixture("single_feature_jsonld.json")
        r = client.get("linked-data/wqp/USGS-05427930?f=jsonld")
        actual = r.json()

        assert actual["@context"] == golden["@context"]

    def test_jsonld_keys_match(self, client):
        """JSON-LD top-level keys match Java."""
        golden = load_fixture("single_feature_jsonld.json")
        r = client.get("linked-data/wqp/USGS-05427930?f=jsonld")
        actual = r.json()

        assert set(golden.keys()) == set(actual.keys())


# ---------------------------------------------------------------------------
# Tier 2: Summary comparison (counts, keys, types)
# ---------------------------------------------------------------------------


class TestFeaturesBySource:
    def test_property_keys_match(self, client):
        """Feature property keys match Java for nwissite source."""
        golden = load_fixture("features_by_source.json")
        r = client.get("linked-data/nwissite?f=json")
        actual = summarize_collection(r.json())

        assert actual["property_keys"] == golden["property_keys"]

    def test_geometry_types_match(self, client):
        golden = load_fixture("features_by_source.json")
        r = client.get("linked-data/nwissite?f=json")
        actual = summarize_collection(r.json())

        assert actual["geometry_types"] == golden["geometry_types"]


class TestNavFlowlines:
    def test_dm_flowline_keys(self, client):
        """DM flowline property keys match Java."""
        golden = load_fixture("nav_dm_flowlines.json")
        r = client.get("linked-data/comid/13293396/navigation/DM/flowlines?distance=10&f=json")
        actual = summarize_collection(r.json())

        assert actual["property_keys"] == golden["property_keys"]

    def test_um_flowline_keys(self, client):
        """UM flowline property keys match Java."""
        golden = load_fixture("nav_um_flowlines.json")
        r = client.get("linked-data/comid/13293396/navigation/UM/flowlines?distance=10&f=json")
        actual = summarize_collection(r.json())

        assert actual["property_keys"] == golden["property_keys"]

    def test_dm_flowline_count_within_tolerance(self, client):
        """DM flowline count is within 10% of Java."""
        golden = load_fixture("nav_dm_flowlines.json")
        r = client.get("linked-data/comid/13293396/navigation/DM/flowlines?distance=10&f=json")
        actual_count = len(r.json()["features"])
        golden_count = golden["feature_count"]

        tolerance = max(golden_count * 0.1, 5)
        assert abs(actual_count - golden_count) <= tolerance, (
            f"Count {actual_count} vs golden {golden_count} (tolerance ±{tolerance:.0f})"
        )


class TestNavFeatures:
    def test_dm_feature_keys(self, client):
        """DM navigated feature property keys match Java."""
        golden = load_fixture("nav_dm_features_wqp.json")
        r = client.get("linked-data/comid/13293396/navigation/DM/wqp?distance=50&f=json")
        actual = summarize_collection(r.json())

        assert actual["property_keys"] == golden["property_keys"]

    def test_dm_feature_count_within_tolerance(self, client):
        """DM navigated feature count is within 10% of Java."""
        golden = load_fixture("nav_dm_features_wqp.json")
        r = client.get("linked-data/comid/13293396/navigation/DM/wqp?distance=50&f=json")
        actual_count = len(r.json()["features"])
        golden_count = golden["feature_count"]

        tolerance = max(golden_count * 0.1, 5)
        assert abs(actual_count - golden_count) <= tolerance, (
            f"Count {actual_count} vs golden {golden_count} (tolerance ±{tolerance:.0f})"
        )
