"""Unit tests for basin split catchment."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


class FakePyGeoAPISplitClient:
    """Fake pygeoapi client that returns a split catchment polygon."""

    async def post(self, path, data, timeout=None):
        if "splitcatchment" in path:
            return {
                "features": [
                    {"id": "mergedCatchment", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}
                ]
            }
        # flowtrace
        return {"features": [{"properties": {"intersection_point": [-89.47, 43.09]}}]}

    async def splitcatchment(self, lon, lat):
        return {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}


def _app_with_fakes(source_repo, feature_repo, flowline_repo, catchment_repo, pygeoapi_client):
    os.environ.setdefault("NLDI_BASE_URL", "https://test.example.com/nldi")
    return create_app(dependencies={
        "source_repo": Provide(lambda: source_repo, sync_to_thread=False),
        "feature_repo": Provide(lambda: feature_repo, sync_to_thread=False),
        "flowline_repo": Provide(lambda: flowline_repo, sync_to_thread=False),
        "catchment_repo": Provide(lambda: catchment_repo, sync_to_thread=False),
        "pygeoapi_client": Provide(lambda: pygeoapi_client, sync_to_thread=False),
    })


class TestBasinSplitCatchment:
    def test_split_catchment_with_comid_returns_400(
        self, fake_source_repo, fake_feature_repo, fake_flowline_repo, fake_catchment_repo
    ):
        app = _app_with_fakes(
            fake_source_repo([]),
            fake_feature_repo([]),
            fake_flowline_repo([]),
            fake_catchment_repo([]),
            FakePyGeoAPISplitClient(),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/123/basin?splitCatchment=true")
            assert r.status_code == 400

    def test_split_catchment_returns_polygon(
        self, fake_source_repo, make_source, fake_feature_repo, make_feature, fake_flowline_repo, make_flowline, fake_catchment_repo, make_catchment
    ):
        """Split catchment should return a polygon when pygeoapi succeeds."""
        app = _app_with_fakes(
            fake_source_repo([make_source("wqp", "WQP")]),
            fake_feature_repo([make_feature("USGS-01", "wqp", "WQP", "Site", "https://example.com", comid=123)]),
            fake_flowline_repo([make_flowline(123)]),
            fake_catchment_repo([make_catchment(123)]),
            FakePyGeoAPISplitClient(),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-01/basin?splitCatchment=true")
            assert r.status_code == 200
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert body["features"][0]["geometry"]["type"] == "Polygon"

    def test_simple_basin_still_works(
        self, fake_source_repo, fake_feature_repo, fake_flowline_repo, fake_catchment_repo, make_catchment
    ):
        """Without splitCatchment, should use the simple basin path."""
        app = _app_with_fakes(
            fake_source_repo([]),
            fake_feature_repo([]),
            fake_flowline_repo([]),
            fake_catchment_repo([make_catchment(13293396)]),
            FakePyGeoAPISplitClient(),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/13293396/basin")
            assert r.status_code == 200
            body = r.json()
            assert body["features"][0]["geometry"]["type"] == "Polygon"
