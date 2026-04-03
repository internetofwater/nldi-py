"""Unit tests for navigation modes and navigation info endpoints."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app


def _app_with_fakes(source_repo):
    os.environ.setdefault("NLDI_BASE_URL", "https://test.example.com/nldi")
    return create_app(dependencies={
        "source_repo": Provide(lambda: source_repo, sync_to_thread=False),
    })


class TestNavigationModes:
    def test_returns_four_modes(self, fake_source_repo, make_source):
        app = _app_with_fakes(fake_source_repo([make_source("wqp", "WQP")]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-01/navigation")
            assert r.status_code == 200
            body = r.json()
            assert "upstreamMain" in body
            assert "upstreamTributaries" in body
            assert "downstreamMain" in body
            assert "downstreamDiversions" in body
            assert body["upstreamMain"].endswith("/navigation/UM")

    def test_unknown_source_returns_404(self, fake_source_repo):
        app = _app_with_fakes(fake_source_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/nosuch/ABC/navigation")
            assert r.status_code == 404

    def test_comid_source_skips_validation(self, fake_source_repo):
        app = _app_with_fakes(fake_source_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/comid/123/navigation")
            assert r.status_code == 200


class TestNavigationInfo:
    def test_returns_sources_with_flowlines_first(self, fake_source_repo, make_source):
        app = _app_with_fakes(fake_source_repo([make_source("wqp", "WQP"), make_source("nwissite", "NWIS")]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-01/navigation/UM")
            assert r.status_code == 200
            body = r.json()
            assert body[0]["source"] == "Flowlines"
            assert len(body) == 3  # flowlines + 2 sources

    def test_invalid_nav_mode_returns_400(self, fake_source_repo, make_source):
        app = _app_with_fakes(fake_source_repo([make_source("wqp", "WQP")]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/wqp/USGS-01/navigation/BOGUS")
            assert r.status_code == 400

    def test_unknown_source_returns_404(self, fake_source_repo):
        app = _app_with_fakes(fake_source_repo([]))
        with TestClient(app=app) as client:
            r = client.get("/api/nldi/linked-data/nosuch/ABC/navigation/UM")
            assert r.status_code == 404
