"""Integration tests for the assembled app."""

from litestar.testing import TestClient

from nldi.asgi import create_app


def _client():
    app = create_app()
    return TestClient(app=app)


def test_landing_page():
    with _client() as client:
        r = client.get("/api/nldi/")
        assert r.status_code == 200
        body = r.json()
        assert "title" in body
        assert "links" in body


def test_health_check():
    with _client() as client:
        r = client.get("/api/nldi/about/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

import pytest

STUB_PATHS = [
    "/api/nldi/linked-data/hydrolocation?coords=POINT(-89 43)",
    "/api/nldi/linked-data/comid/position?coords=POINT(-89 43)",
    "/api/nldi/linked-data/wqp",
    "/api/nldi/linked-data/wqp/USGS-01/basin",
    "/api/nldi/linked-data/wqp/USGS-01/navigation",
    "/api/nldi/linked-data/wqp/USGS-01/navigation/UM",
    "/api/nldi/linked-data/wqp/USGS-01/navigation/UM/flowlines",
    "/api/nldi/linked-data/wqp/USGS-01/navigation/UM/nwissite",
]


@pytest.mark.parametrize("path", STUB_PATHS)
def test_linked_data_stubs_return_501(path):
    with _client() as client:
        r = client.get(path)
        assert r.status_code == 501


def test_cors_headers_on_response():
    with _client() as client:
        r = client.get("/api/nldi/")
        assert r.headers.get("access-control-allow-origin") == "*"
        assert "cache-control" in r.headers
        assert "Accept" in r.headers.get("vary", "")


def test_invalid_f_on_linked_data_returns_400():
    with _client() as client:
        r = client.get("/api/nldi/linked-data/wqp?f=xml")
        assert r.status_code == 400


def test_unknown_route_returns_problem_json():
    with _client() as client:
        r = client.get("/api/nldi/nonexistent")
        assert r.status_code == 404
        assert r.headers.get("content-type") == "application/problem+json"


def test_head_landing_page():
    with _client() as client:
        r = client.head("/api/nldi/")
        assert r.status_code == 200
        assert r.content == b""


def test_head_linked_data_stub():
    with _client() as client:
        r = client.head("/api/nldi/linked-data/wqp")
        assert r.status_code == 200
        assert r.content == b""


def test_head_nonexistent_returns_404():
    with _client() as client:
        r = client.head("/api/nldi/nonexistent")
        assert r.status_code == 404


def test_swagger_ui_redirects_to_docs():
    with _client() as client:
        r = client.get("/api/nldi/swagger-ui/index.html", follow_redirects=False)
        assert r.status_code == 301
        assert "/api/nldi/docs" in r.headers["location"]


def test_openapi_redirects_to_docs():
    with _client() as client:
        r = client.get("/api/nldi/openapi", follow_redirects=False)
        assert r.status_code == 301
        assert "/api/nldi/docs" in r.headers["location"]
