# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ASGI application factory."""

from litestar import Litestar
from litestar.logging import LoggingConfig

from . import __version__
from .config import get_log_level, get_prefix


def create_app() -> Litestar:
    return Litestar(
        route_handlers=[],
        path=get_prefix(),
        logging_config=LoggingConfig(root={"level": get_log_level(), "handlers": ["queue_listener"]}),
    )


app = create_app()
