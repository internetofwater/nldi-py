# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Client for pygeoapi external service calls.

Handles timeouts and connection errors with distinct exceptions
so the API can return 504 Gateway Timeout vs 500 Internal Server Error.
"""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20  # seconds


class PyGeoAPIError(Exception):
    """Error communicating with pygeoapi service."""


class PyGeoAPITimeoutError(PyGeoAPIError):
    """Timeout communicating with pygeoapi service."""


class PyGeoAPIClient:
    """Async HTTP client for pygeoapi service."""

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        """Initialize with pygeoapi base URL and default timeout."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def post(self, path: str, data: dict, timeout: int | None = None) -> dict:
        """POST to a pygeoapi endpoint. Returns parsed JSON response."""
        url = f"{self.base_url}/{path}"
        _timeout = timeout or self.timeout
        logger.info("POST (timeout=%s) to: %s", _timeout, url)

        try:
            async with httpx.AsyncClient(verify=False) as client:  # noqa: S501
                r = await client.post(url, content=json.dumps(data), timeout=_timeout)
                r.raise_for_status()
                return r.json()
        except httpx.TimeoutException as e:
            raise PyGeoAPITimeoutError(f"Timeout calling {url}: {e}") from e
        except httpx.ConnectError as e:
            raise PyGeoAPIError(f"Cannot connect to {url}: {e}") from e
        except httpx.HTTPStatusError as e:
            raise PyGeoAPIError(f"HTTP error from {url}: {e}") from e
        except json.JSONDecodeError as e:
            raise PyGeoAPIError(f"Invalid JSON from {url}: {e}") from e

    async def splitcatchment(self, lon: float, lat: float) -> dict | None:
        """Call pygeoapi splitcatchment service. Returns the merged catchment feature or None."""
        payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": str(lon)},
                {"id": "lat", "type": "text/plain", "value": str(lat)},
                {"id": "upstream", "type": "text/plain", "value": "true"},
            ]
        }
        response = await self.post(
            "processes/nldi-splitcatchment/execution",
            payload,
            timeout=self.timeout * 2,  # split is slow
        )
        for feature in response.get("features", []):
            if feature.get("id") in ("mergedCatchment", "drainageBasin"):
                feature.pop("id", None)
                return feature
        return None
