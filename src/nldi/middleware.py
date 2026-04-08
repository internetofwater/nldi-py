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

import asyncio
import logging
import uuid
from time import perf_counter

from litestar.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

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


def timing_middleware_factory(app: ASGIApp) -> ASGIApp:
    """Log request start/end with timing and a short correlation ID."""

    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return

        req_id = uuid.uuid4().hex[:8]
        qs = scope.get("query_string", b"").decode()
        path = f"{scope['path']}?{qs}" if qs else scope["path"]
        logger.info("[%s] %s %s - started", req_id, scope["method"], path)
        start = perf_counter()
        try:
            await app(scope, receive, send)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning("[%s] Connection lost during %s %s: %s", req_id, scope["method"], scope["path"], e)
        finally:
            elapsed = perf_counter() - start
            logger.info("[%s] %s %s: %.3fs", req_id, scope["method"], scope["path"], elapsed)

    return middleware


def disconnect_guard_factory(app: ASGIApp) -> ASGIApp:
    """Cancel in-flight DB queries when the client disconnects.

    Monitors the ASGI ``receive`` channel for ``http.disconnect``. When
    detected, calls ``cancel_running_query()`` on any repos registered
    in ``scope["_repos"]``, then cancels the handler task.

    Only effective for navigation/basin queries that set ``_cancel_pid``
    in the repo before executing expensive CTEs.
    """

    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return

        scope["_repos"] = []
        disconnect = asyncio.Event()

        async def guarded_receive() -> dict:
            msg = await receive()
            if msg["type"] == "http.disconnect":
                disconnect.set()
            return msg

        handler = asyncio.create_task(app(scope, guarded_receive, send))

        async def watch() -> None:
            await disconnect.wait()
            for repo in scope.get("_repos", []):
                try:
                    await repo.cancel_running_query()
                except Exception:  # noqa: S110
                    pass
            handler.cancel()

        watcher = asyncio.create_task(watch())

        try:
            await handler
        except asyncio.CancelledError:
            logger.info("Request cancelled by client disconnect")
        finally:
            watcher.cancel()

    return middleware
