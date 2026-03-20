#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""ASGI application factory for NLDI API server."""

import logging

from advanced_alchemy.config.engine import EngineConfig
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.logging import LoggingConfig
from litestar.openapi.config import OpenAPIConfig, SwaggerRenderPlugin
from litestar.openapi.spec import Tag

from . import __version__
from .config import get_config, log_level
from .server.linked_data.endpoints import LinkedDataController
from .server.root.endpoints import RootController


def create_app() -> Litestar:
    _cfg = get_config()

    alchemy_plugin = SQLAlchemyPlugin(
        config=SQLAlchemyAsyncConfig(
            connection_string=_cfg.db.URL,
            create_all=False,
            engine_config=EngineConfig(pool_pre_ping=True, pool_size=10, max_overflow=10, pool_recycle=300, pool_timeout=30),
        )
    )

    app = Litestar(
        route_handlers=[RootController, LinkedDataController],
        plugins=[alchemy_plugin],
        cors_config=CORSConfig(allow_origins=["*"]),
        logging_config=LoggingConfig(root={"level": log_level(), "handlers": ["queue_listener"]}),
        on_startup=[lambda app: setattr(app.state, "nldi_config", _cfg)],
        path=_cfg.server.prefix,
        openapi_config=OpenAPIConfig(
            title=_cfg.metadata.title,
            version=__version__,
            path="/docs",
            render_plugins=[SwaggerRenderPlugin()],
            use_handler_docstrings=True,
            tags=[
                Tag(
                    name="nldi",
                    description="Root NLDI services",
                ),
                Tag(
                    name="by_comid",
                    description="Endpoints that only work against the `comid` source. 'comid' can always be used as a source in `by_sourceid` endpoints.",
                ),
                Tag(
                    name="by_sourceid",
                    description="lookups by a source name (`source_name`); 'comid' is always a valid source. A list of all sources is available at the `/linked-data` endpoint.",
                ),
            ],
        ),
    )
    return app


APP = create_app()
