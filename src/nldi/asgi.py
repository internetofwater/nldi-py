# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ASGI application factory."""

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from advanced_alchemy.extensions.litestar.plugins.init.config.engine import EngineConfig
from litestar import Litestar
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from . import __version__
from .config import get_database_url, get_log_level, get_prefix
from .controllers.linked_data import LinkedDataController, provide_source_repo
from .controllers.root import RootController
from .errors import problem_details_handler, unhandled_exception_handler
from .middleware import headers_middleware_factory


def _db_plugin() -> list:
    """Return SQLAlchemy plugin if DB env vars are set, else empty list."""
    try:
        url = get_database_url()
    except RuntimeError:
        return []
    return [
        SQLAlchemyPlugin(
            config=SQLAlchemyAsyncConfig(
                connection_string=url,
                create_all=False,
                engine_config=EngineConfig(
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=10,
                ),
            )
        )
    ]


def create_app(dependencies: dict | None = None) -> Litestar:
    """Create and configure the Litestar ASGI application."""
    deps = {"source_repo": Provide(provide_source_repo)}
    if dependencies:
        deps.update(dependencies)
    return Litestar(
        route_handlers=[RootController, LinkedDataController],
        path=get_prefix(),
        plugins=_db_plugin(),
        dependencies=deps,
        logging_config=LoggingConfig(root={"level": get_log_level(), "handlers": ["queue_listener"]}),
        exception_handlers={  # ty: ignore[invalid-argument-type]
            HTTPException: problem_details_handler,
            Exception: unhandled_exception_handler,
        },
        middleware=[headers_middleware_factory],
        openapi_config=OpenAPIConfig(
            title="Network Linked Data Index API",
            version=__version__,
            path="/docs",
            render_plugins=[SwaggerRenderPlugin()],
        ),
    )


app = create_app()
