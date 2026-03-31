from litestar import Litestar, get
from litestar.exceptions import NotFoundException
from litestar.testing import TestClient


def _make_app() -> Litestar:
    from nldi.errors import problem_details_handler, unhandled_exception_handler

    @get("/found")
    async def found_route() -> dict:
        return {"ok": True}

    @get("/missing")
    async def missing_route() -> dict:
        raise NotFoundException(detail="Thing not found")

    @get("/broken")
    async def broken_route() -> dict:
        raise RuntimeError("something broke internally")

    return Litestar(
        route_handlers=[found_route, missing_route, broken_route],
        exception_handlers={
            NotFoundException: problem_details_handler,
            Exception: unhandled_exception_handler,
        },
    )


def test_not_found_returns_problem_json():
    with TestClient(app=_make_app()) as client:
        r = client.get("/missing")
        assert r.status_code == 404
        assert r.headers["content-type"] == "application/problem+json"
        body = r.json()
        assert body["type"] == "about:blank"
        assert body["title"] == "Not Found"
        assert body["status"] == 404
        assert body["detail"] == "Thing not found"


def test_bad_request_returns_problem_json():
    from litestar.exceptions import ClientException

    def _make_app_400():
        from nldi.errors import problem_details_handler, unhandled_exception_handler

        @get("/bad")
        async def bad_route() -> dict:
            raise ClientException(detail="Invalid parameter")

        return Litestar(
            route_handlers=[bad_route],
            exception_handlers={ClientException: problem_details_handler, Exception: unhandled_exception_handler},
        )

    with TestClient(app=_make_app_400()) as client:
        r = client.get("/bad")
        assert r.status_code == 400
        assert r.headers["content-type"] == "application/problem+json"
        body = r.json()
        assert body["title"] == "Bad Request"
        assert body["detail"] == "Invalid parameter"


def test_unhandled_exception_returns_500_problem_json():
    with TestClient(app=_make_app()) as client:
        r = client.get("/broken")
        assert r.status_code == 500
        assert r.headers["content-type"] == "application/problem+json"
        body = r.json()
        assert body["type"] == "about:blank"
        assert body["title"] == "Internal Server Error"
        assert body["status"] == 500
        assert body["detail"] == "An unexpected error occurred."
        assert "instance" in body
        assert body["instance"].startswith("urn:error:")


def test_500_does_not_leak_internal_details():
    with TestClient(app=_make_app()) as client:
        r = client.get("/broken")
        body = r.text
        assert "something broke internally" not in body
        assert "Traceback" not in body
        assert "RuntimeError" not in body


def test_500_logs_reference_id():
    from unittest.mock import patch

    with patch("nldi.errors.logger") as mock_logger:
        with TestClient(app=_make_app()) as client:
            r = client.get("/broken")
            ref = r.json()["instance"].split(":")[-1]
            mock_logger.exception.assert_called_once()
            logged_ref = mock_logger.exception.call_args[0][1]
            assert logged_ref == ref
