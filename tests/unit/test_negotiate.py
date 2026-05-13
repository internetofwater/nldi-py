from litestar import Litestar, get
from litestar.testing import TestClient


def _make_app() -> Litestar:
    from nldi.negotiate import check_format

    @get("/test")
    async def test_route(f: str = "") -> dict:
        return {"format": f}

    return Litestar(route_handlers=[test_route], before_request=check_format)


def test_f_json_passes_through():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test?f=json")
        assert r.status_code == 200
        assert r.json()["format"] == "json"


def test_f_jsonld_passes_through():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test?f=jsonld")
        assert r.status_code == 200
        assert r.json()["format"] == "jsonld"


def test_f_html_passes_through():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test?f=html")
        assert r.status_code == 200
        assert r.json()["format"] == "html"


def test_f_empty_passes_through():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test")
        assert r.status_code == 200
        assert r.json()["format"] == ""


def test_f_invalid_returns_400():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test?f=xml")
        assert r.status_code == 400


def test_browser_redirect_when_no_f_and_accept_html():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test", headers={"Accept": "text/html"}, follow_redirects=False)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "f=json" in r.text


def test_no_f_accept_json_passes_through():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test", headers={"Accept": "application/json"})
        assert r.status_code == 200
        assert r.json()["format"] == ""


def test_explicit_f_overrides_accept_html():
    with TestClient(app=_make_app()) as client:
        r = client.get("/test?f=json", headers={"Accept": "text/html"})
        assert r.status_code == 200
        assert r.json()["format"] == "json"


def test_browser_redirect_uses_public_base_url(monkeypatch):
    """The HTML redirect link must use NLDI_URL/NLDI_PATH, not the request host.

    When behind a reverse proxy (CloudFront), ``request.url`` reflects the
    origin-facing scheme and host, not the viewer-facing ones. The redirect
    link must use the configured public base URL so viewers get a working
    link.
    """
    monkeypatch.setenv("NLDI_URL", "https://public.example.com")
    monkeypatch.setenv("NLDI_PATH", "/nldi")

    from litestar import Litestar, get
    from nldi.negotiate import check_format

    @get("/linked-data/nwissite/{identifier:str}")
    async def feature(identifier: str, f: str = "") -> dict:
        return {"format": f, "id": identifier}

    app = Litestar(route_handlers=[feature], path="/nldi", before_request=check_format)

    with TestClient(app=app) as client:
        # TestClient uses http://testserver as the host (origin-facing, like
        # the CloudFront distribution hostname in production).
        r = client.get(
            "/nldi/linked-data/nwissite/USGS-11120000",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        # The link must use the public base URL, not testserver
        assert "https://public.example.com/nldi/linked-data/nwissite/USGS-11120000" in r.text
        assert "testserver" not in r.text
        assert "f=json" in r.text
