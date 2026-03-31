# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Content negotiation: f= query parameter validation and browser redirect."""

from litestar import Response
from litestar.connection import Request
from litestar.exceptions import ClientException

VALID_FORMATS = {"json", "jsonld", "html", ""}

HTML_REDIRECT_TEMPLATE = """<!doctype html>
<html><body>
<p>This is a JSON API. <a href="{url}">View as JSON</a>.</p>
</body></html>"""


async def check_format(request: Request) -> Response | None:
    """Validate the f= query parameter and handle browser redirect.

    If f= is present and invalid, raises 400.
    If f= is absent and the client accepts text/html (browser), returns
    a small HTML page linking to the JSON version.
    """
    f = request.query_params.get("f", "")

    if f not in VALID_FORMATS:
        raise ClientException(detail=f"Invalid format '{f}'. Must be one of: json, jsonld, html")

    if not f and "text/html" in request.headers.get("accept", ""):
        sep = "&" if "?" in str(request.url) else "?"
        json_url = f"{request.url}{sep}f=json"
        return Response(
            content=HTML_REDIRECT_TEMPLATE.format(url=json_url),
            status_code=200,
            media_type="text/html",
        )

    return None
