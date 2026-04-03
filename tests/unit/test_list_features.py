"""Unit tests for GET /linked-data/{source_name} (list features by source)."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


def _app_with_fakes(source_repo, feature_repo, flowline_repo):
    os.environ.setdefault("NLDI_BASE_URL", "https://test.example.com/nldi")
    return create_app(dependencies={
        "source_repo": Provide(lambda: source_repo, sync_to_thread=False),
        "feature_repo": Provide(lambda: feature_repo, sync_to_thread=False),
        "flowline_repo": Provide(lambda: flowline_repo, sync_to_thread=False),
    })


class TestListFeatures:
    def test_unknown_source_returns_404(self, fake_source_repo, fake_feature_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_source_repo([]), fake_feature_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/nosuch")
            assert r.status_code == 404

    def test_known_source_returns_feature_collection(
        self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo
    ):
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "WQP")]),
            fake_feature_repo([
                make_feature("USGS-01", "wqp", "WQP", "Site 1", "https://example.com/1"),
                make_feature("USGS-02", "wqp", "WQP", "Site 2", "https://example.com/2"),
            ]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp")
            assert r.status_code == 200
            assert r.headers["content-type"] == "application/geo+json"
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert len(body["features"]) == 2

    def test_empty_source_returns_empty_collection(
        self, fake_source_repo, make_source, fake_feature_repo, fake_flowline_repo
    ):
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "WQP")]),
            fake_feature_repo([]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp")
            assert r.status_code == 200
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert len(body["features"]) == 0

    def test_pagination_limits_results(
        self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo
    ):
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "WQP")]),
            fake_feature_repo([
                make_feature("USGS-01", "wqp", "WQP", "Site 1", "https://example.com/1"),
                make_feature("USGS-02", "wqp", "WQP", "Site 2", "https://example.com/2"),
                make_feature("USGS-03", "wqp", "WQP", "Site 3", "https://example.com/3"),
            ]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp?limit=2")
            body = r.json()
            assert len(body["features"]) == 2
