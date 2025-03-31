#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""
Controllers and route handlers for the "system" (i.e. infrastructure) endpoints.

System endpoints include the essential furniture ("/", "/robots.txt", "/favicon.ico")
as well as system information endpoints -- healthcheck being one example.
"""

from copy import deepcopy
from typing import Any

import litestar

from nldi import util
from nldi.config import MasterConfig


class RootController(litestar.Controller):
    """Controller/route-handler for all of the base endpoints."""

    tags = ["system"]

    @litestar.get("/", include_in_schema=False, media_type=litestar.MediaType.JSON)
    async def root(self, state: litestar.datastructures.State) -> dict[str, str|list]:
        content = {
            "title": state.cfg.metadata.title,
            "description": state.cfg.metadata.description,
            "links": [
                {
                    "rel": "data",
                    "type": "application/json",
                    "title": "Sources",
                    "href": util.url_join(state.cfg.server.base_url, "linked-data"),
                },
                {
                    "rel": "service-desc",
                    "type": "text/html",
                    "title": "The OpenAPI definition as HTML",
                    "href": util.url_join(state.cfg.server.base_url, "docs"),
                },
                {
                    "rel": "service-desc",
                    "type": "application/vnd.oai.openapi+json;version=3.0",
                    "title": "The OpenAPI definition as JSON",
                    "href": util.url_join(state.cfg.server.base_url, "docs", "openapi.json"),
                },
            ],
        }
        return content
        ## NOTE:  The default paths for the openapi docs and the rendering endpoint are different under LiteStar than
        ## under the flask implementation.  Do we need to make those match exactly?  The above paths are correct, but
        ## they are slightly different than the flask implementation.

    @litestar.get("/robots.txt", include_in_schema=False, sync_to_thread=False, media_type=litestar.MediaType.TEXT)
    def robots_txt(self) -> litestar.response.Response:
        """Disable crawlers from scanning this server."""
        return litestar.response.Response(
            content="User-agent: *\nDisallow: /\n",
            status_code=200,
            media_type=litestar.MediaType.TEXT,
        )

    @litestar.get("/favicon.ico", include_in_schema=False, sync_to_thread=False)
    def favicon_ico(self) -> None:
        """Dummy endpoint for the favicon."""
        return None
