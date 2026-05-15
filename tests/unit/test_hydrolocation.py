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


class FakePyGeoAPIClientUpstream400:
    """Fake pygeoapi client that raises a PyGeoAPIError with upstream 400 + detail."""

    async def post(self, path, data, timeout=None):
        from nldi.pygeoapi import PyGeoAPIError
        raise PyGeoAPIError(
            "HTTP 400 from upstream",
            upstream_status=400,
            upstream_detail="Error executing process: The NLDI GeoServer failed to return a catchment.",
        )


class FakePyGeoAPIClientUpstream429:
    """Fake pygeoapi client that raises a PyGeoAPIError with upstream 429."""

    async def post(self, path, data, timeout=None):
        from nldi.pygeoapi import PyGeoAPIError
        raise PyGeoAPIError(
            "HTTP 429 from upstream",
            upstream_status=429,
            upstream_detail="Too many requests",
        )


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

    def test_pygeoapi_upstream_400_returns_502_with_detail(self, fake_catchment_repo, fake_flowline_repo):
        """Upstream 4xx from pygeoapi returns 502 problem+json with upstream detail."""
        app = _app_with_fakes(
            fake_catchment_repo([]),
            fake_flowline_repo([]),
            FakePyGeoAPIClientUpstream400(),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/hydrolocation?coords=POINT(-89.509 43.087)")
            assert r.status_code == 502
            assert r.headers["content-type"].startswith("application/problem+json")
            body = r.json()
            assert body["status"] == 502
            assert "NLDI GeoServer failed to return a catchment" in body["detail"]

    def test_pygeoapi_upstream_429_returns_502_with_detail(self, fake_catchment_repo, fake_flowline_repo):
        """Upstream 429 from pygeoapi returns 502 problem+json."""
        app = _app_with_fakes(
            fake_catchment_repo([]),
            fake_flowline_repo([]),
            FakePyGeoAPIClientUpstream429(),
        )
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/hydrolocation?coords=POINT(-89.509 43.087)")
            assert r.status_code == 502
            body = r.json()
            assert body["status"] == 502
            assert "Too many requests" in body["detail"]
