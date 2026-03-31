# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Root controller — landing page and health check."""

from litestar import Controller, Request, route

from ..helpers import head_response
from ..media import MediaType


class RootController(Controller):
    """System-level endpoints."""

    path = ""
    tags = ["nldi"]

    @route("/", http_method=["GET", "HEAD"], media_type=MediaType.JSON)
    async def landing_page(self, request: Request) -> dict:
        """Landing page."""
        if request.method == "HEAD":
            return head_response()
        return {
            "title": "Network Linked Data Index API",
            "description": "NLDI API",
            "links": [
                {"rel": "data", "type": MediaType.JSON, "title": "Sources", "href": "linked-data"},
                {"rel": "service-doc", "type": MediaType.HTML, "title": "API docs", "href": "docs"},
                {
                    "rel": "service-desc",
                    "type": MediaType.OPENAPI_JSON,
                    "title": "OpenAPI definition",
                    "href": "docs/openapi.json",
                },
            ],
        }

    @route("/about/health", http_method=["GET", "HEAD"], include_in_schema=False)
    async def health_check(self, request: Request) -> dict:
        """Health check."""
        if request.method == "HEAD":
            return head_response()
        return {"status": "ok"}
