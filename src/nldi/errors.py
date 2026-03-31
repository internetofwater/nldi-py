# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""RFC 9457 Problem Details error handlers."""

import logging
import uuid
from http import HTTPStatus
from typing import Any

from litestar import Request, Response
from litestar.exceptions import HTTPException

from .media import MediaType

logger = logging.getLogger(__name__)


def problem_details_handler(_request: Request[Any, Any, Any], exc: HTTPException) -> Response[dict[str, Any]]:
    """Return an RFC 9457 Problem Details response for HTTP exceptions."""
    title = HTTPStatus(exc.status_code).phrase if exc.status_code in HTTPStatus else "Error"
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": exc.status_code,
        "detail": exc.detail,
    }
    return Response(content=body, status_code=exc.status_code, media_type=MediaType.PROBLEM_JSON)


def unhandled_exception_handler(_request: Request[Any, Any, Any], exc: Exception) -> Response[dict[str, Any]]:
    """Return a generic 500 Problem Details response for unhandled exceptions.

    Logs the full traceback server-side with a reference ID.
    The reference ID is returned to the client via the ``instance`` field
    so it can be used to correlate error reports with log entries.
    """
    ref = uuid.uuid4().hex[:8]
    logger.exception("Unhandled exception [%s]", ref)
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": f"urn:error:{ref}",
    }
    return Response(content=body, status_code=500, media_type=MediaType.PROBLEM_JSON)
