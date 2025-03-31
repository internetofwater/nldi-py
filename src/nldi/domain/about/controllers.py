#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""
Controllers and route handlers for the "system" (i.e. infrastructure) endpoints.

System endpoints include the essential furniture ("/", "/robots.txt", "/favicon.ico")as
well as system information endpoints -- healthcheck being one example.
"""

from copy import deepcopy
from typing import Any, Literal, TypeVar

import litestar
from sqlalchemy.ext.asyncio import AsyncSession

from nldi import __version__
from nldi.config import MasterConfig, status


class AboutController(litestar.Controller):
    """Controller/route-handler for all of the "about" endpoints."""

    path = "/about"
    tags = ["system"]

    @litestar.get(
        "/health",
        summary="App Service Health Check",
        media_type=litestar.MediaType.JSON,
    )
    async def healthcheck(self, state: litestar.datastructures.State) -> status.SystemHealth:
        """Simple healthcheck for app and its dependent services."""
        return status.SystemHealth(
            server=state.cfg.server.healthstatus(),
            db=state.cfg.db.healthstatus(),
            pygeoapi=state.cfg.server.healthstatus("pygeoapi"),
        )

    @litestar.get("/health/db", include_in_schema=False)
    async def healthcheck_database(self, state: litestar.datastructures.State) -> status.ServiceHealth:
        return state.cfg.db.healthstatus()

    @litestar.get("/health/pygeoapi", include_in_schema=False)
    async def healthcheck_pygeoapi(self, state: litestar.datastructures.State) -> status.ServiceHealth:
        return state.cfg.server.healthstatus("pygeoapi")

    @litestar.get("/config", include_in_schema=False, media_type=litestar.MediaType.JSON)
    async def app_configuration(self, state: litestar.datastructures.State) -> MasterConfig:
        """Display the master config as JSON."""
        _sanitized_config = deepcopy(state.cfg)
        _sanitized_config.db.password = "***"  # noqa: S105
        return _sanitized_config

    @litestar.get(path=["/", "/info"], include_in_schema=False, media_type=litestar.MediaType.JSON)
    async def app_info(self, request: litestar.Request) -> dict[str, Any]:
        _ = request
        return {
            "name": "nldi-py",
            "version": __version__,
        }
