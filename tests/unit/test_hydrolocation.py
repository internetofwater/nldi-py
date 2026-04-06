"""Unit tests for hydrolocation endpoint."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


class FakePyGeoAPIClient:
    """Fake pygeoapi client that returns a canned flowtrace response."""

    async def post(self, path, data, timeout=None):
        return {
            "features": [{
                "properties": {
                    "intersection_point": [-89.472, 43.098]
                }
            }]
        }


class FakePyGeoAPIClientTimeout:
    """Fake pygeoapi client that raises timeout."""

    async def post(self, path, data, timeout=None):
        from nldi.pygeoapi import PyGeoAPITimeoutError
        raise PyGeoAPITimeoutError("timed out")


def _app_with_fakes(catchment_repo, flowline_repo, pygeoapi_client):
    os.environ.setdefault("NLDI_URL", "https://test.example.com")
    return create_app(dependencies={
        "catchment_repo": Provide(lambda: catchment_repo, sync_to_thread=False),
        "flowline_repo": Provide(lambda: flowline_repo, sync_to_thread=False),
        "pygeoapi_client": Provide(lambda: pygeoapi_client, sync_to_thread=False),
    })


class TestHydrolocation:
    def test_missing_coords_returns_400(self, fake_catchment_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_catchment_repo([]), fake_flowline_repo([]), FakePyGeoAPIClient())
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/hydrolocation")
            assert r.status_code == 400

    def test_invalid_coords_returns_400(self, fake_catchment_repo, fake_flowline_repo):
        app = _app_with_fakes(fake_catchment_repo([]), fake_flowline_repo([]), FakePyGeoAPIClient())
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/hydrolocation?coords=NOTAPOINT")
            assert r.status_code == 400

    def test_valid_coords_returns_two_features(
        self, fake_catchment_repo, make_catchment, fake_flowline_repo, make_flowline
    ):
        app = _app_with_fakes(
            fake_catchment_repo([make_catchment(13294314)]),
            fake_flowline_repo([make_flowline(13294314)]),
            FakePyGeoAPIClient(),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/hydrolocation?coords=POINT(-89.509 43.087)")
            assert r.status_code == 200
            body = r.json()
            assert body["type"] == "FeatureCollection"
            assert len(body["features"]) == 2
            assert body["features"][0]["properties"]["source"] == "indexed"
            assert body["features"][1]["properties"]["source"] == "provided"

    def test_pygeoapi_timeout_returns_504(self, fake_catchment_repo, fake_flowline_repo):
        app = _app_with_fakes(
            fake_catchment_repo([]),
            fake_flowline_repo([]),
            FakePyGeoAPIClientTimeout(),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/hydrolocation?coords=POINT(-89.509 43.087)")
            assert r.status_code == 504
