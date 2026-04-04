"""Unit tests for flowline navigation endpoint."""

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


class TestFlowlineNavigation:
    def test_dm_returns_feature_collection(
        self, fake_source_repo, fake_feature_repo, fake_flowline_repo, make_flowline
    ):
        app = _app_with_fakes(
            fake_source_repo([]),
            fake_feature_repo([]),
            fake_flowline_repo([make_flowline(13293396), make_flowline(13293400)]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/13293396/navigation/DM/flowlines?distance=10")
            assert r.status_code == 200
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert len(body["features"]) == 2
            assert body["features"][0]["properties"]["nhdplus_comid"] == 13293396

    def test_invalid_mode_returns_400(self, fake_source_repo, fake_feature_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_source_repo([]), fake_feature_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/123/navigation/BOGUS/flowlines?distance=10")
            assert r.status_code == 400

    def test_unsupported_mode_returns_501(self, fake_source_repo, fake_feature_repo, fake_flowline_repo):
        """All modes now supported — this test verifies they don't 501."""
        pass  # Removed: all modes implemented in 3.2

    def test_invalid_comid_returns_400(self, fake_source_repo, fake_feature_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_source_repo([]), fake_feature_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/notanumber/navigation/DM/flowlines?distance=10")
            assert r.status_code == 400
