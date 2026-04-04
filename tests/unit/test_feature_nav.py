"""Unit tests for feature navigation by data source."""

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


class TestFeatureNavigation:
    def test_returns_feature_collection(
        self, fake_source_repo, fake_feature_repo, make_feature, fake_flowline_repo
    ):
        app = _app_with_fakes(
            fake_source_repo([]),
            fake_feature_repo([make_feature("USGS-01", "wqp", "WQP", "Site 1", "https://example.com/1")]),
            fake_flowline_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/123/navigation/DM/wqp?distance=10")
            assert r.status_code == 200
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert len(body["features"]) == 1
            assert body["features"][0]["properties"]["source"] == "wqp"

    def test_invalid_mode_returns_400(self, fake_source_repo, fake_feature_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_source_repo([]), fake_feature_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/123/navigation/BOGUS/wqp?distance=10")
            assert r.status_code == 400
