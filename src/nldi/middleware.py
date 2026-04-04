# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ASGI middleware for explicit HTTP headers.

Litestar provides built-in CORSConfig, but we implement CORS headers explicitly
because CORSConfig only adds headers when it sees an Origin request header.
Behind a reverse proxy that strips Origin, CORS headers silently disappear.
This middleware adds them unconditionally.

HEAD is handled at the route level using @head decorators with
multi-path arrays, excluded from the OpenAPI schema.

See docs/principles.md #3: "Explicit over magical."
"""

from litestar.types import ASGIApp, Receive, Scope, Send

CORS_HEADERS = [
    (b"access-control-allow-origin", b"*"),
    (b"access-control-allow-methods", b"GET, HEAD, OPTIONS"),
]

STANDARD_HEADERS = [
    *CORS_HEADERS,
    (b"cache-control", b"public, max-age=3600"),
    (b"vary", b"Accept, Origin"),
]


def headers_middleware_factory(app: ASGIApp) -> ASGIApp:
    """Wrap an ASGI app to inject standard HTTP headers on every response."""

    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                existing_keys = {k for k, _v in message.get("headers", [])}
                extra = [h for h in STANDARD_HEADERS if h[0] not in existing_keys]
                message["headers"] = list(message.get("headers", [])) + extra
            await send(message)

        await app(scope, receive, send_with_headers)

    return middleware
