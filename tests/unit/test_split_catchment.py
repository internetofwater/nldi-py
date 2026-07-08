"""Unit tests for split catchment building blocks."""



async def test_splitcatchment_client_returns_feature(monkeypatch):
    """splitcatchment extracts mergedCatchment from response."""
    from nldi.pygeoapi import PyGeoAPIClient

    async def mock_post(self, url, **kwargs):
        class R:
            status_code = 200

            def json(self):
                return {
                    "features": [
                        {"id": "otherFeature", "geometry": {"type": "Point"}},
                        {"id": "mergedCatchment", "geometry": {"type": "Polygon", "coordinates": []}},
                    ]
                }

            def raise_for_status(self):
                pass

        return R()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi")
    result = await client.splitcatchment(-89.5, 43.1)
    assert result is not None
    assert result["geometry"]["type"] == "Polygon"
    assert "id" not in result


async def test_splitcatchment_client_handles_drainage_basin_id(monkeypatch):
    """splitcatchment also accepts drainageBasin as the feature id."""
    from nldi.pygeoapi import PyGeoAPIClient

    async def mock_post(self, url, **kwargs):
        class R:
            status_code = 200

            def json(self):
                return {"features": [{"id": "drainageBasin", "geometry": {"type": "Polygon"}}]}

            def raise_for_status(self):
                pass

        return R()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi")
    result = await client.splitcatchment(-89.5, 43.1)
    assert result is not None


async def test_splitcatchment_client_returns_none_if_no_match(monkeypatch):
    """splitcatchment returns None if no mergedCatchment/drainageBasin found."""
    from nldi.pygeoapi import PyGeoAPIClient

    async def mock_post(self, url, **kwargs):
        class R:
            status_code = 200

            def json(self):
                return {"features": [{"id": "somethingElse", "geometry": {}}]}

            def raise_for_status(self):
                pass

        return R()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi")
    result = await client.splitcatchment(-89.5, 43.1)
    assert result is None


async def test_splitcatchment_uses_double_timeout(monkeypatch):
    """splitcatchment should use 2x the normal timeout."""
    from nldi.pygeoapi import PyGeoAPIClient

    captured_timeout = None

    async def mock_post(self, url, **kwargs):
        nonlocal captured_timeout
        captured_timeout = kwargs.get("timeout")

        class R:
            status_code = 200

            def json(self):
                return {"features": []}

            def raise_for_status(self):
                pass

        return R()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = PyGeoAPIClient("https://fake.example.com/pygeoapi", timeout=15)
    await client.splitcatchment(-89.5, 43.1)
    assert captured_timeout == 30
