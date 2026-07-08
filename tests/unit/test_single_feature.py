"""Unit tests for single feature endpoint."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


def _app_with_fakes(source_repo, feature_repo, flowline_repo):
    """Create app with fake repos injected."""
    os.environ.setdefault("NLDI_URL", "https://test.example.com")
    return create_app(dependencies={
        "source_repo": Provide(lambda: source_repo, sync_to_thread=False),
        "feature_repo": Provide(lambda: feature_repo, sync_to_thread=False),
        "flowline_repo": Provide(lambda: flowline_repo, sync_to_thread=False),
    })


class TestSingleFeature:
    def test_unknown_source_returns_404(self, fake_source_repo, fake_feature_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_source_repo([]), fake_feature_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/nosuch/ABC")
            assert r.status_code == 404

    def test_unknown_identifier_returns_404(self, fake_source_repo, make_source, fake_feature_repo, fake_flowline_repo):
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "WQP")]),
            fake_feature_repo([]),  # no features
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/NOSUCH")
            assert r.status_code == 404

    def test_known_feature_returns_feature_collection(
        self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo
    ):
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "Water Quality Portal")]),
            fake_feature_repo([make_feature("USGS-01", "wqp", "Water Quality Portal", "Test Site", "https://example.com/USGS-01")]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-01")
            assert r.status_code == 200
            assert r.headers["content-type"] == "application/geo+json"
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert len(body["features"]) == 1
            props = body["features"][0]["properties"]
            assert props["identifier"] == "USGS-01"
            assert props["source"] == "wqp"
            assert props["sourceName"] == "Water Quality Portal"
            assert "navigation" in props
            assert props["navigation"].endswith("/linked-data/wqp/USGS-01/navigation")

    def test_feature_includes_measure_property(
        self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo
    ):
        """Feature properties must include 'measure' (parity with Java NLDI)."""
        feat = make_feature("USGS-01", "wqp", "Water Quality Portal", "Test Site", "https://example.com/USGS-01")
        feat.measure = 42.5
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "Water Quality Portal")]),
            fake_feature_repo([feat]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-01")
            assert r.status_code == 200
            props = r.json()["features"][0]["properties"]
            assert "measure" in props
            assert props["measure"] == 42.5

    def test_feature_measure_is_null_when_absent(
        self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo
    ):
        """When the DB measure is NULL, the 'measure' property should be null."""
        feat = make_feature("USGS-02", "wqp", "Water Quality Portal", "Test Site", "https://example.com/USGS-02")
        # feat.measure is None by default in the fake
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "Water Quality Portal")]),
            fake_feature_repo([feat]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-02")
            assert r.status_code == 200
            props = r.json()["features"][0]["properties"]
            assert "measure" in props
            assert props["measure"] is None

    def test_invalid_comid_returns_400(self, fake_source_repo, fake_feature_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_source_repo([]), fake_feature_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/notanumber")
            assert r.status_code == 400
