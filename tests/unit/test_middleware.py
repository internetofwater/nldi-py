from litestar import Litestar, get
from litestar.testing import TestClient

from nldi.middleware import headers_middleware_factory


def _make_app() -> Litestar:
    @get("/test")
    async def test_route() -> dict:
        return {"ok": True}

    app = Litestar(route_handlers=[test_route], middleware=[headers_middleware_factory])
    return app


def test_cors_allow_origin():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test")
        assert r.headers.get("access-control-allow-origin") == "*"


def test_cors_allow_methods():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test")
        assert r.headers.get("access-control-allow-methods") == "GET, HEAD, OPTIONS"


def test_options_preflight():
    with TestClient(app=_make_app()) as client:
        r = client.options("/test")
        assert r.headers.get("access-control-allow-origin") == "*"


def test_cache_control():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test")
        assert "cache-control" in r.headers


def test_vary_header():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test")
        assert "Accept" in r.headers.get("vary", "")
        assert "Origin" in r.headers.get("vary", "")
