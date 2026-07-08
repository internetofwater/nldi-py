"""Unit tests for f=jsonld on endpoints."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


def _app_with_fakes(source_repo, feature_repo, flowline_repo):
    os.environ.setdefault("NLDI_URL", "https://test.example.com")
    return create_app(dependencies={
        "source_repo": Provide(lambda: source_repo, sync_to_thread=False),
        "feature_repo": Provide(lambda: feature_repo, sync_to_thread=False),
        "flowline_repo": Provide(lambda: flowline_repo, sync_to_thread=False),
    })


class TestJsonLdEndpoints:
    def test_single_feature_jsonld(self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo):
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "WQP")]),
            fake_feature_repo([make_feature("USGS-01", "wqp", "WQP", "Test", "https://example.com", comid=123)]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-01?f=jsonld")
            assert r.status_code == 200
            assert r.headers["content-type"] == "application/ld+json"
            body = r.json()
            assert "@context" in body
            assert "@id" in body
            assert "@graph" not in body  # single feature, no graph wrapper

    def test_list_features_jsonld(self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo):
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "WQP")]),
            fake_feature_repo([
                make_feature("USGS-01", "wqp", "WQP", "A", "https://example.com/1", comid=1),
                make_feature("USGS-02", "wqp", "WQP", "B", "https://example.com/2", comid=2),
            ]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp?f=jsonld")
            assert r.status_code == 200
            assert r.headers["content-type"] == "application/ld+json"
            body = r.json()
            assert "@context" in body
            assert "@graph" in body
            assert len(body["@graph"]) == 2

    def test_feature_nav_jsonld(self, fake_source_repo, fake_feature_repo, make_feature, fake_flowline_repo):
        app = _app_with_fakes(
            fake_source_repo([]),
            fake_feature_repo([make_feature("USGS-01", "wqp", "WQP", "A", "https://example.com", comid=1)]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/123/navigation/DM/wqp?distance=10&f=jsonld")
            assert r.status_code == 200
            assert r.headers["content-type"] == "application/ld+json"
