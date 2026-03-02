#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Root controller for system-level endpoints."""

import logging

import msgspec
from litestar import Controller, Response, get
from litestar.response import Redirect

from ... import __version__, util
from .. import AppState


class RootController(Controller):
    path = ""

    @get("/")
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

    @get("/about/health")
    async def healthcheck(self, state: AppState) -> dict:
        """Health check for server and its dependent services."""
        _cfg = state.nldi_config
        return {
            "server": msgspec.structs.asdict(_cfg.server.healthstatus()),
            "db": msgspec.structs.asdict(_cfg.db.healthstatus()),
            "pygeoapi": msgspec.structs.asdict(_cfg.server.healthstatus("pygeoapi")),
        }

    @get("/docs/openapi.json", media_type="application/vnd.oai.openapi+json;version=3.0")
    async def openapi_json(self) -> dict:
        """OpenAPI specification as JSON."""
        from ..openapi import generate_openapi_json

        return generate_openapi_json()

    @get("/docs", media_type="text/html")
    async def openapi_ui(self) -> str:
        """Swagger UI."""
        data = {"openapi-document-path": "openapi.json"}
        return util.render_j2_template("swagger.html", data)

    @get("/openapi")
    async def openapi_redirect(self) -> Redirect:
        return Redirect(path="docs")
