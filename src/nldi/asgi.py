# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ASGI application factory."""

import asyncio
import logging

import sqlalchemy.exc
from litestar import Litestar
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.router import Router

from . import __description__, __title__, __version__
from .config import get_log_level, get_prefix
from .controllers.linked_data import (
    provide_catchment_repo,
    provide_feature_repo,
    provide_flowline_repo,
    provide_pygeoapi_client,
    provide_source_repo,
)
from .controllers.linked_data.basin import BasinController
from .controllers.linked_data.lookups import LookupController
from .controllers.linked_data.navigation import NavigationController
from .controllers.root import RootController
from .db import provide_db_session
from .errors import (
    db_unavailable_handler,
    gateway_timeout_handler,
    problem_details_handler,
    unhandled_exception_handler,
)
from .middleware import disconnect_guard_factory, headers_middleware_factory, timing_middleware_factory
from .pygeoapi import PyGeoAPITimeoutError

_logger = logging.getLogger(__name__)


async def _log_pending_tasks() -> None:
    """Log any tasks still running at shutdown."""
    current = asyncio.current_task()
    pending = [t for t in asyncio.all_tasks() if not t.done() and t is not current]
    if pending:
        _logger.warning("Shutdown: %d pending task(s)", len(pending))


def create_app(dependencies: dict | None = None) -> Litestar:
    """Create and configure the Litestar ASGI application."""
    deps = {
        "db_session": Provide(provide_db_session),
        "source_repo": Provide(provide_source_repo),
        "feature_repo": Provide(provide_feature_repo),
        "flowline_repo": Provide(provide_flowline_repo),
        "catchment_repo": Provide(provide_catchment_repo),
        "pygeoapi_client": Provide(provide_pygeoapi_client, sync_to_thread=False),
    }
    if dependencies:
        deps.update(dependencies)
    linked_data_router = Router(
        path="/",
        route_handlers=[LookupController, NavigationController, BasinController],
        middleware=[disconnect_guard_factory, timing_middleware_factory],
    )
    return Litestar(
        route_handlers=[RootController, linked_data_router],
        path=get_prefix(),
        dependencies=deps,
        logging_config=LoggingConfig(root={"level": get_log_level(), "handlers": ["queue_listener"]}),
        exception_handlers={  # ty: ignore[invalid-argument-type]
            HTTPException: problem_details_handler,
            PyGeoAPITimeoutError: gateway_timeout_handler,
            sqlalchemy.exc.SQLAlchemyError: db_unavailable_handler,
            TimeoutError: db_unavailable_handler,
            Exception: unhandled_exception_handler,
        },
        middleware=[headers_middleware_factory],
        on_shutdown=[_log_pending_tasks],
        openapi_config=OpenAPIConfig(
            title=__title__,
            version=__version__,
            path="/docs",
            render_plugins=[SwaggerRenderPlugin()],
            use_handler_docstrings=True,
        ),
    )


app = create_app()
