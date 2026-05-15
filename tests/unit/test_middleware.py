from typing import Annotated

from litestar import Litestar, get, route
from litestar.di import Provide
from litestar.params import Dependency
from litestar.testing import TestClient

from nldi.middleware import head_shortcircuit_factory, headers_middleware_factory


def _make_app() -> Litestar:
    @get("/test")
    async def test_route() -> dict:
        return {"ok": True}

    app = Litestar(route_handlers=[test_route], middleware=[headers_middleware_factory])
    return app


def _make_heavy_app() -> Litestar:
    """App with a handler that injects a 'source_repo' dependency."""
    call_flag: dict = {"called": False}

    async def provide_source_repo() -> str:
        return "repo"

    @route("/heavy", http_method=["GET", "HEAD"])
    async def heavy_handler(source_repo: Annotated[str, Dependency(skip_validation=True)]) -> dict:
        call_flag["called"] = True
        return {"data": "expensive"}

    @route("/light", http_method=["GET", "HEAD"])
    async def light_handler() -> dict:
        return {"data": "cheap"}

    app = Litestar(
        route_handlers=[heavy_handler, light_handler],
        middleware=[headers_middleware_factory, head_shortcircuit_factory],
        dependencies={"source_repo": Provide(provide_source_repo)},
    )
    return app, call_flag


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


# --- HEAD short-circuit middleware tests ---


def test_head_does_not_invoke_repository():
    """T5: HEAD on a DB-backed endpoint does not call the handler."""
    app, call_flag = _make_heavy_app()
    with TestClient(app=app) as client:
        r = client.head("/heavy")
        assert r.status_code == 200
        assert r.content == b""
        assert call_flag["called"] is False


def test_head_passes_through_light_handler():
    """HEAD on a lightweight endpoint passes through to the handler."""
    app, _ = _make_heavy_app()
    with TestClient(app=app) as client:
        r = client.head("/light")
        assert r.status_code == 200


def test_head_invalid_format_returns_400_from_middleware():
    """HEAD with invalid f= on a heavy endpoint returns 400."""
    app, _ = _make_heavy_app()
    with TestClient(app=app) as client:
        r = client.head("/heavy?f=xml")
        assert r.status_code == 400
        assert r.headers.get("content-type") == "application/problem+json"


def test_head_valid_format_returns_200():
    """HEAD with valid f= on a heavy endpoint returns 200."""
    app, _ = _make_heavy_app()
    with TestClient(app=app) as client:
        r = client.head("/heavy?f=json")
        assert r.status_code == 200
        assert r.content == b""


def test_get_still_works_on_heavy_handler():
    """GET on a heavy endpoint still executes the handler."""
    app, call_flag = _make_heavy_app()
    with TestClient(app=app) as client:
        r = client.get("/heavy")
        assert r.status_code == 200
        assert call_flag["called"] is True
