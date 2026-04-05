# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Root controller — landing page and health check."""

from litestar import Controller, Response, get, head
from litestar.response import Redirect

from .. import __description__, __title__
from ..config import get_prefix
from ..health import health_status
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
            "title": __title__,
            "description": __description__,
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
    async def health_check(self) -> Response:
        """Health check for server and dependent services."""
        data = await health_status()
        return Response(content=data, headers={"cache-control": "no-cache, no-store, max-age=0"})

    @get("/swagger-ui/index.html", include_in_schema=False)
    async def swagger_ui_redirect(self) -> Redirect:
        """Redirect legacy Java Swagger UI path to docs."""
        return Redirect(path=f"{get_prefix()}/docs", status_code=301)

    @get("/openapi", include_in_schema=False)
    async def openapi_redirect(self) -> Redirect:
        """Redirect legacy OpenAPI path to docs."""
        return Redirect(path=f"{get_prefix()}/docs", status_code=301)
