"""Unit tests for GET /linked-data/comid/position."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


def _app_with_fakes(catchment_repo, flowline_repo):
    os.environ.setdefault("NLDI_BASE_URL", "https://test.example.com/nldi")
    return create_app(dependencies={
        "catchment_repo": Provide(lambda: catchment_repo, sync_to_thread=False),
        "flowline_repo": Provide(lambda: flowline_repo, sync_to_thread=False),
    })


class TestFlowlineByPosition:
    def test_missing_coords_returns_400(self, fake_catchment_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_catchment_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/position")
            assert r.status_code == 400

    def test_no_catchment_returns_404(self, fake_catchment_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_catchment_repo([]), fake_flowline_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/position?coords=POINT(-89 43)")
            assert r.status_code == 404

    def test_valid_coords_returns_feature_collection(
        self, fake_catchment_repo, make_catchment, fake_flowline_repo, make_flowline
    ):
        app = _app_with_fakes(
            fake_catchment_repo([make_catchment(13293396)]),
            fake_flowline_repo([make_flowline(13293396)]),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/position?coords=POINT(-89 43)")
            assert r.status_code == 200
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert body["features"][0]["properties"]["comid"] == 13293396
