#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Settings and utilities for OpenAPI document generation."""

from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import RedocRenderPlugin, SwaggerRenderPlugin

from .. import __version__
from ..config import get_config

__cfg = get_config()

config = OpenAPIConfig(
    title=__cfg.metadata.title,
    description=__cfg.metadata.description,
    license=__cfg.metadata.license,
    terms_of_service=__cfg.metadata.terms_of_service,
    version=__version__,
    use_handler_docstrings=True,
    path="/openapi",
    render_plugins=[
        SwaggerRenderPlugin(path="/swagger"),
        RedocRenderPlugin(path="/redoc", google_fonts=True, version="next"),
    ],
)
