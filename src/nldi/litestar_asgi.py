#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""ASGI server implementation"""

import os
import pathlib

import litestar
from litestar.contrib.sqlalchemy.plugins import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar.logging import LoggingConfig

from . import __version__
from .config import MasterConfig, get_config
from .server import litestar_routers as routers
from .server import openapi

logging_config = LoggingConfig(
    root={"level": "DEBUG", "handlers": ["queue_listener"]},
    formatters={"standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
    log_exceptions="always",
)


def append_headers_to_response(response: litestar.Response) -> litestar.Response:
    response.headers.update(
        {
            "X-Powered-By": f"nldi {__version__} and LiteStar",
        }
    )
    return response


def litestar_app_factory() -> litestar.Litestar:
    """
    Creates a Litestar ASGI app.

    :return: A Litestar app, suited for use in ASGI server (uvicorn, gunicorn, etc.)
    :rtype: litestar.Litestar
    """
    _cfg = get_config()

    sqa_config = SQLAlchemyAsyncConfig(
        connection_string=_cfg.db.URL,
        session_config=AsyncSessionConfig(expire_on_commit=False),
        create_all=False,
    )

    return litestar.Litestar(
        openapi_config=openapi.config,
        route_handlers=routers.route_handlers,
        state=litestar.datastructures.State(state={"cfg": _cfg}),
        logging_config=logging_config,
        plugins=[SQLAlchemyPlugin(config=sqa_config)],
        path=_cfg.server.prefix,
        after_request=append_headers_to_response,
    )


app = litestar_app_factory()
