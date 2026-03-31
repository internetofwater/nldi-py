# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ASGI middleware for explicit HTTP headers.

Litestar provides built-in CORSConfig, but we implement CORS headers explicitly
because CORSConfig only adds headers when it sees an Origin request header.
Behind a reverse proxy that strips Origin, CORS headers silently disappear.
This middleware adds them unconditionally.

Litestar does not automatically handle HEAD for GET routes (unlike Spring Boot,
which the Java implementation relies on). Our middleware intercepts HEAD at the
ASGI layer and returns 200 with headers immediately — no route handler execution,
no wasted DB queries.

By owning these headers explicitly, the app behaves correctly regardless of what
sits between it and the client (proxy, CDN, load balancer).

See docs/principles.md #3: "Explicit over magical."
"""

from litestar.types import ASGIApp, Receive, Scope, Send

from .media import MediaType

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

        if scope["method"] == "HEAD":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", MediaType.JSON.encode()),
                        *STANDARD_HEADERS,
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + STANDARD_HEADERS
            await send(message)

        await app(scope, receive, send_with_headers)

    return middleware
