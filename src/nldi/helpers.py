# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Shared route helpers."""

from litestar import Response

from .media import MediaType


def head_response(media_type: str = MediaType.JSON, status_code: int = 200) -> Response:
    """Return an empty response for HEAD requests with appropriate headers."""
    return Response(content=b"", status_code=status_code, media_type=media_type)
