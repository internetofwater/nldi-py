from litestar.testing import TestClient

from nldi.asgi import create_app


def test_app_creates():
    app = create_app()
    assert app is not None


def test_app_responds():
    app = create_app()
    with TestClient(app=app) as client:
        # No routes defined yet, so root should 404 (or whatever litestar returns)
        r = client.get("/api/nldi/")
        assert r.status_code in (404, 200)  # no routes = 404 is fine
