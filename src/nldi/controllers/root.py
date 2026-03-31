# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Root controller — landing page and health check."""

from litestar import Controller, get, head
from litestar.response import Redirect

from ..media import MediaType


class RootController(Controller):
    """System-level endpoints."""

    path = ""
    tags = ["nldi"]

    @head(["/", "/about/health"], include_in_schema=False)
    async def handle_head(self) -> None:
        """HEAD support for all root endpoints."""
        return None

    @get("/", media_type=MediaType.JSON)
    async def landing_page(self) -> dict:
        """Landing page."""
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

    @get("/about/health", include_in_schema=False)
    async def health_check(self) -> dict:
        """Health check."""
        return {"status": "ok"}

    @get("/swagger-ui/index.html", include_in_schema=False)
    async def swagger_ui_redirect(self) -> Redirect:
        """Redirect legacy Java Swagger UI path to docs."""
        return Redirect(path="/api/nldi/docs", status_code=301)

    @get("/openapi", include_in_schema=False)
    async def openapi_redirect(self) -> Redirect:
        """Redirect legacy OpenAPI path to docs."""
        return Redirect(path="/api/nldi/docs", status_code=301)
