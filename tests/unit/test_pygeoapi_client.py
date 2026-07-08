"""Unit tests for pygeoapi client."""

import pytest


def test_client_imports():
    from nldi.pygeoapi import PyGeoAPIClient

    assert PyGeoAPIClient is not None


async def test_post_success(monkeypatch):
    from nldi.pygeoapi import PyGeoAPIClient

    async def mock_post(self, url, **kwargs):
        class MockResponse:
            status_code = 200
            def json(self): return {"result": "ok"}
            def raise_for_status(self): pass
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi")
    result = await client.post("processes/test/execution", {"input": "data"})
    assert result == {"result": "ok"}


async def test_post_timeout_raises(monkeypatch):
    import httpx
    from nldi.pygeoapi import PyGeoAPIClient, PyGeoAPITimeoutError

    async def mock_post(self, url, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi")
    with pytest.raises(PyGeoAPITimeoutError):
        await client.post("processes/test/execution", {})


async def test_post_connect_error_raises(monkeypatch):
    import httpx
    from nldi.pygeoapi import PyGeoAPIClient, PyGeoAPIError

    async def mock_post(self, url, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi")
    with pytest.raises(PyGeoAPIError, match="connection"):
        await client.post("processes/test/execution", {})


async def test_post_http_error_captures_upstream_detail(monkeypatch):
    """PyGeoAPIError from an HTTP error must carry upstream status and body detail."""
    import httpx
    from nldi.pygeoapi import PyGeoAPIClient, PyGeoAPIError

    async def mock_post(self, url, **kwargs):
        request = httpx.Request("POST", url)
        response = httpx.Response(
            status_code=400,
            request=request,
            json={
                "type": "InvalidParameterValue",
                "code": "InvalidParameterValue",
                "description": "Error executing process: The NLDI GeoServer failed to return a catchment.",
            },
        )
        return response

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi")
    with pytest.raises(PyGeoAPIError) as exc_info:
        await client.post("processes/test/execution", {})

    err = exc_info.value
    assert err.upstream_status == 400
    assert "NLDI GeoServer failed to return a catchment" in err.upstream_detail
