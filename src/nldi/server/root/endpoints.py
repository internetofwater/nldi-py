#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Root controller for system-level endpoints."""

import logging

import litestar
import msgspec
from litestar.enums import MediaType
from litestar.response import Redirect

from ... import __version__, util
from .. import AppState


class RootController(litestar.Controller):
    path = ""
    tags = ["nldi"]

    @litestar.get("/", media_type=MediaType.JSON)
    async def home(self, state: AppState) -> dict:
        """Landing Page"""
        _cfg = state.nldi_config
        return {
            "title": _cfg.metadata.title,
            "description": _cfg.metadata.description,
            "links": [
                {
                    "rel": "data",
                    "type": "application/json",
                    "title": "Sources",
                    "href": util.url_join(_cfg.server.base_url, "linked-data"),
                },
                {
                    "rel": "service-desc",
                    "type": "text/html",
                    "title": "The OpenAPI definition as HTML",
                    "href": util.url_join(_cfg.server.base_url, "docs"),
                },
                {
                    "rel": "service-desc",
                    "type": "application/vnd.oai.openapi+json;version=3.0",
                    "title": "The OpenAPI definition as JSON",
                    "href": util.url_join(_cfg.server.base_url, "docs", "openapi.json"),
                },
            ],
        }

    @litestar.get("/about/health", include_in_schema=False)
    async def healthcheck(self, state: AppState) -> dict:
        """Health check for server and its dependent services."""
        _cfg = state.nldi_config
        return {
            "server": msgspec.structs.asdict(_cfg.server.healthstatus()),
            "db": msgspec.structs.asdict(_cfg.db.healthstatus()),
            "pygeoapi": msgspec.structs.asdict(_cfg.server.healthstatus("pygeoapi")),
        }



    @litestar.get("/openapi", include_in_schema=False)
    async def openapi_redirect(self, request: litestar.Request) -> Redirect:
        _prefix = request.app.path
        _openapi = request.app.openapi_config.path

        return Redirect(path=f"{_prefix}{self.path}{_openapi}")
