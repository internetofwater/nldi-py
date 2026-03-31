# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ASGI application factory."""

from litestar import Litestar
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from . import __version__
from .config import get_log_level, get_prefix
from .controllers.linked_data import LinkedDataController
from .controllers.root import RootController
from .errors import problem_details_handler, unhandled_exception_handler
from .middleware import headers_middleware_factory
from .negotiate import check_format


def create_app() -> Litestar:
    """Create and configure the Litestar ASGI application."""
    app = Litestar(
        route_handlers=[RootController, LinkedDataController],
        path=get_prefix(),
        logging_config=LoggingConfig(root={"level": get_log_level(), "handlers": ["queue_listener"]}),
        exception_handlers={
            HTTPException: problem_details_handler,
            Exception: unhandled_exception_handler,
        },
        openapi_config=OpenAPIConfig(
            title="Network Linked Data Index API",
            version=__version__,
            path="/docs",
            render_plugins=[SwaggerRenderPlugin()],
        ),
    )
    app.asgi_handler = headers_middleware_factory(app.asgi_handler)
    return app


app = create_app()
