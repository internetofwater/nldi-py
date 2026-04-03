"""Unit tests for GET /linked-data (list sources) endpoint."""

import os

from litestar.di import Provide
from litestar.testing import TestClient

from nldi.asgi import create_app
from nldi.dto import DataSource


def _app_with_fake_sources(sources, fake_source_repo_cls):
    """Create app with fake source repo injected at app level."""
    os.environ.setdefault("NLDI_BASE_URL", "https://test.example.com/nldi")
    fake = fake_source_repo_cls(sources)
    return create_app(dependencies={"source_repo": Provide(lambda: fake, sync_to_thread=False)})


def test_list_sources_returns_comid_first(fake_source_repo, make_source):
    app = _app_with_fake_sources([make_source("wqp", "Water Quality Portal")], fake_source_repo)
    with TestClient(app=app) as client:
        r = client.get("/api/nldi/linked-data/")
        assert r.status_code == 200
        body = r.json()
        assert body[0]["source"] == "comid"
        assert body[0]["sourceName"] == "NHDPlus comid"


def test_list_sources_includes_db_sources(fake_source_repo, make_source):
    app = _app_with_fake_sources(
        [make_source("wqp", "Water Quality Portal"), make_source("nwissite", "NWIS Sites")],
        fake_source_repo,
    )
    with TestClient(app=app) as client:
        r = client.get("/api/nldi/linked-data/")
        body = r.json()
        assert len(body) == 3
        sources = [s["source"] for s in body]
        assert "wqp" in sources
        assert "nwissite" in sources


def test_list_sources_features_urls_use_base_url(monkeypatch, fake_source_repo, make_source):
    monkeypatch.setenv("NLDI_BASE_URL", "https://custom.example.com/api")
    app = _app_with_fake_sources([make_source("wqp", "WQP")], fake_source_repo)
    with TestClient(app=app) as client:
        r = client.get("/api/nldi/linked-data/")
        body = r.json()
        assert body[0]["features"] == "https://custom.example.com/api/linked-data/comid"
        assert body[1]["features"] == "https://custom.example.com/api/linked-data/wqp"


def test_list_sources_empty_db(fake_source_repo):
    app = _app_with_fake_sources([], fake_source_repo)
    with TestClient(app=app) as client:
        r = client.get("/api/nldi/linked-data/")
        body = r.json()
        assert len(body) == 1
        assert body[0]["source"] == "comid"


def test_datasource_dto():
    ds = DataSource(source="wqp", sourceName="Water Quality Portal", features="https://example.com/linked-data/wqp")
    assert ds.source == "wqp"
    assert ds.sourceName == "Water Quality Portal"
    assert ds.features == "https://example.com/linked-data/wqp"
