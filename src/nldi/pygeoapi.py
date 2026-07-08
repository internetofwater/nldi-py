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


def _extract_upstream_detail(response: "httpx.Response") -> str:
    """Pull a human-readable error detail from a pygeoapi error response.

    pygeoapi typically returns JSON like::

        {"type": "...", "code": "...", "description": "..."}

    Other services may use ``detail`` or ``message``. Falls back to the
    raw text body (truncated) if nothing structured is found.
    """
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError):
        text = (response.text or "").strip()
        return text[:500]

    if isinstance(body, dict):
        for key in ("description", "detail", "message"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
    return str(body)[:500]


class PyGeoAPIError(Exception):
    """Error communicating with pygeoapi service.

    Carries optional upstream context when the error originated from an
    HTTP response — ``upstream_status`` is the response code and
    ``upstream_detail`` is a human-readable description extracted from
    the response body (pygeoapi returns JSON with ``description``,
    ``detail``, or ``message`` fields).
    """

    def __init__(
        self,
        message: str,
        upstream_status: int | None = None,
        upstream_detail: str = "",
    ):
        """Initialize with an error message and optional upstream context.

        :param message: Internal error message (logged, not sent to client).
        :param upstream_status: HTTP status returned by the upstream service.
        :param upstream_detail: Human-readable detail from the upstream
            response body, safe to expose in the API response.
        """
        super().__init__(message)
        self.upstream_status = upstream_status
        self.upstream_detail = upstream_detail


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
                if r.status_code >= 400:
                    detail = _extract_upstream_detail(r)
                    raise PyGeoAPIError(
                        f"HTTP {r.status_code} from {url}: {detail or r.reason_phrase}",
                        upstream_status=r.status_code,
                        upstream_detail=detail,
                    )
                return r.json()
        except httpx.TimeoutException as e:
            raise PyGeoAPITimeoutError(f"Timeout calling {url}: {e}") from e
        except httpx.ConnectError as e:
            raise PyGeoAPIError(f"Cannot connect to {url}: {e}") from e
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
