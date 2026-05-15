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
        body = r.json()
        assert "server" in body
        assert "db" in body
        assert "pygeoapi" in body
        assert body["server"]["status"] == "online"
        assert "no-cache" in r.headers.get("cache-control", "")



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


def test_options_landing_page():
    # Characterizes current Litestar behavior: OPTIONS returns 204 with an
    # Allow header. The exact methods listed are not asserted here because
    # of an upstream Litestar bug where the Allow header can omit methods
    # registered via separate decorators on the same path. See
    # docs/litestar-options-bug-report.md for details.
    with _client() as client:
        r = client.options("/api/nldi/")
        assert r.status_code == 204
        assert "OPTIONS" in r.headers.get("allow", "")
        assert r.headers.get("access-control-allow-origin") == "*"


def test_options_linked_data_endpoint():
    # See note on test_options_landing_page above. We assert HEAD and OPTIONS
    # are present (these survive the bug); GET is intentionally not asserted
    # because it is currently dropped from the Allow header for paths
    # covered by both @head and @get.
    with _client() as client:
        r = client.options("/api/nldi/linked-data/wqp")
        assert r.status_code == 204
        allow = r.headers.get("allow", "")
        assert "HEAD" in allow
        assert "OPTIONS" in allow


def test_options_nonexistent_returns_404():
    with _client() as client:
        r = client.options("/api/nldi/nonexistent")
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
