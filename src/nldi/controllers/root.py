# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Root controller — landing page and health check."""

from litestar import Controller, get
from litestar.enums import MediaType


class RootController(Controller):
    """System-level endpoints."""

    path = ""
    tags = ["nldi"]

    @get("/", media_type=MediaType.JSON)
    async def landing_page(self) -> dict:
        """Landing page."""
        return {
            "title": "Network Linked Data Index API",
            "description": "NLDI API",
            "links": [
                {"rel": "data", "type": "application/json", "title": "Sources", "href": "linked-data"},
                {"rel": "service-doc", "type": "text/html", "title": "API docs", "href": "docs"},
                {
                    "rel": "service-desc",
                    "type": "application/vnd.oai.openapi+json;version=3.1",
                    "title": "OpenAPI definition",
                    "href": "docs/openapi.json",
                },
            ],
        }

    @get("/about/health", include_in_schema=False)
    async def health_check(self) -> dict:
        """Health check."""
        return {"status": "ok"}
