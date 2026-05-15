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
    """T1: OPTIONS on landing page returns GET, HEAD, OPTIONS in Allow."""
    with _client() as client:
        r = client.options("/api/nldi/")
        assert r.status_code == 204
        allow = r.headers.get("allow", "")
        assert "GET" in allow
        assert "HEAD" in allow
        assert "OPTIONS" in allow
        assert r.headers.get("access-control-allow-origin") == "*"


def test_options_linked_data_endpoint():
    """T2: OPTIONS on linked-data endpoint returns GET, HEAD, OPTIONS in Allow."""
    with _client() as client:
        r = client.options("/api/nldi/linked-data/wqp")
        assert r.status_code == 204
        allow = r.headers.get("allow", "")
        assert "GET" in allow
        assert "HEAD" in allow
        assert "OPTIONS" in allow


def test_options_nonexistent_returns_404():
    with _client() as client:
        r = client.options("/api/nldi/nonexistent")
        assert r.status_code == 404


def test_options_navigation_endpoint():
    """T3: OPTIONS on a navigation endpoint returns GET, HEAD, OPTIONS in Allow."""
    with _client() as client:
        r = client.options("/api/nldi/linked-data/wqp/USGS-01/navigation")
        assert r.status_code == 204
        allow = r.headers.get("allow", "")
        assert "GET" in allow
        assert "HEAD" in allow
        assert "OPTIONS" in allow


def test_options_basin_endpoint():
    """T4: OPTIONS on basin endpoint returns GET, HEAD, OPTIONS in Allow."""
    with _client() as client:
        r = client.options("/api/nldi/linked-data/wqp/USGS-01/basin")
        assert r.status_code == 204
        allow = r.headers.get("allow", "")
        assert "GET" in allow
        assert "HEAD" in allow
        assert "OPTIONS" in allow


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


# --- Characterization tests: lock in HEAD behavior before refactor ---


def test_head_landing_page_headers():
    """C1: HEAD on root returns 200 + empty body + CORS headers."""
    with _client() as client:
        r = client.head("/api/nldi/")
        assert r.status_code == 200
        assert r.content == b""
        assert r.headers.get("access-control-allow-origin") == "*"
        assert "cache-control" in r.headers
        assert "vary" in r.headers


def test_head_health_check():
    """C2: HEAD on health returns 200 + empty body."""
    with _client() as client:
        r = client.head("/api/nldi/about/health")
        assert r.status_code == 200
        assert r.content == b""


def test_head_linked_data_source_headers():
    """C3: HEAD on linked-data source returns 200 + empty body + headers."""
    with _client() as client:
        r = client.head("/api/nldi/linked-data/wqp")
        assert r.status_code == 200
        assert r.content == b""
        assert r.headers.get("access-control-allow-origin") == "*"


def test_head_invalid_format_returns_400():
    """C7: HEAD with invalid f= returns 400."""
    with _client() as client:
        r = client.head("/api/nldi/linked-data/wqp?f=xml")
        assert r.status_code == 400


def test_head_swagger_redirect():
    """C5: HEAD on swagger-ui redirect returns 301 + Location + empty body."""
    with _client() as client:
        r = client.head("/api/nldi/swagger-ui/index.html", follow_redirects=False)
        assert r.status_code == 301
        assert "/api/nldi/docs" in r.headers["location"]
        assert r.content == b""


def test_head_openapi_redirect():
    """C6: HEAD on openapi redirect returns 301 + Location + empty body."""
    with _client() as client:
        r = client.head("/api/nldi/openapi", follow_redirects=False)
        assert r.status_code == 301
        assert "/api/nldi/docs" in r.headers["location"]
        assert r.content == b""
