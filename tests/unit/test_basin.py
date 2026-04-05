"""Unit tests for basin endpoint."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


def _app_with_fakes(source_repo, feature_repo, flowline_repo, catchment_repo):
    os.environ.setdefault("NLDI_BASE_URL", "https://test.example.com/nldi")
    return create_app(dependencies={
        "source_repo": Provide(lambda: source_repo, sync_to_thread=False),
        "feature_repo": Provide(lambda: feature_repo, sync_to_thread=False),
        "flowline_repo": Provide(lambda: flowline_repo, sync_to_thread=False),
        "catchment_repo": Provide(lambda: catchment_repo, sync_to_thread=False),
    })


class TestBasin:
    def test_comid_basin_returns_polygon(
        self, fake_source_repo, fake_feature_repo, fake_flowline_repo, fake_catchment_repo, make_catchment
    ):
        app = _app_with_fakes(
            fake_source_repo([]),
            fake_feature_repo([]),
            fake_flowline_repo([]),
            fake_catchment_repo([make_catchment(13293396)]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/13293396/basin")
            assert r.status_code == 200
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert len(body["features"]) == 1
            assert body["features"][0]["geometry"]["type"] == "Polygon"
            assert body["features"][0]["properties"] == {}

    def test_invalid_comid_returns_400(
        self, fake_source_repo, fake_feature_repo, fake_flowline_repo, fake_catchment_repo
    ):
        app = _app_with_fakes(
            fake_source_repo([]),
            fake_feature_repo([]),
            fake_flowline_repo([]),
            fake_catchment_repo([]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/notanumber/basin")
            assert r.status_code == 400
