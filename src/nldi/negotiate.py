# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Content negotiation: f= query parameter validation and browser redirect."""

from litestar import Response
from litestar.connection import Request
from litestar.exceptions import ClientException

from .config import get_base_url, get_prefix
from .media import MediaType

VALID_FORMATS = {"json", "jsonld", "html", ""}

HTML_REDIRECT_TEMPLATE = """<!doctype html>
<html><body>
<p>This is a JSON API. <a href="{url}">View as JSON</a>.</p>
</body></html>"""


def validate_format_param(query_string: bytes) -> str | None:
    """Check the f= query parameter against VALID_FORMATS.

    :param query_string: Raw query string bytes from the ASGI scope.
    :returns: An error message string if invalid, or ``None`` if valid.
    """
    from urllib.parse import parse_qs

    params = parse_qs(query_string.decode())
    f_values = params.get("f", [""])
    f = f_values[0] if f_values else ""
    if f not in VALID_FORMATS:
        options = ", ".join(sorted(VALID_FORMATS - {""}))
        return f"Invalid format '{f}'. Must be one of: {options}"
    return None


async def check_format(request: Request) -> Response | None:
    """Validate the f= query parameter and handle browser redirect.

    If f= is present and invalid, raises 400.
    If f= is absent and the client accepts text/html (browser), returns
    a small HTML page linking to the JSON version.

    The link is built from the configured public base URL (``NLDI_URL`` +
    ``NLDI_PATH``) rather than ``request.url``, because behind a reverse
    proxy (e.g. CloudFront) ``request.url`` reflects the origin-facing
    scheme and host, not the viewer-facing ones.
    """
    f = request.query_params.get("f", "")

    if f not in VALID_FORMATS:
        options = ", ".join(sorted(VALID_FORMATS - {""}))
        raise ClientException(detail=f"Invalid format '{f}'. Must be one of: {options}")

    if not f and MediaType.HTML in request.headers.get("accept", ""):
        # Rebuild the URL using the public base URL, preserving only the
        # path-after-prefix and the original query string.
        base_url = get_base_url()
        prefix = get_prefix()
        path = request.url.path
        if prefix and path.startswith(prefix):
            path = path[len(prefix) :]
        query = request.url.query
        sep = "&" if query else "?"
        json_url = f"{base_url}{path}{'?' + query if query else ''}{sep}f=json"
        return Response(
            content=HTML_REDIRECT_TEMPLATE.format(url=json_url),
            status_code=200,
            media_type=MediaType.HTML,
        )

    return None
