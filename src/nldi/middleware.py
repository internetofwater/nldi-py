# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ASGI middleware for explicit HTTP headers and HEAD short-circuit.

Litestar provides built-in CORSConfig, but we implement CORS headers explicitly
because CORSConfig only adds headers when it sees an Origin request header.
Behind a reverse proxy that strips Origin, CORS headers silently disappear.
This middleware adds them unconditionally.

HEAD requests on endpoints that inject a repository or pygeoapi_client
dependency are short-circuited by ``head_shortcircuit_factory`` at the
app-level middleware layer. The handler body never executes, so no DB
connections are acquired and no upstream calls are made. Lightweight
endpoints (redirects, landing page, health) pass through to the GET
handler, and Litestar handles HEAD response semantics automatically.

See docs/principles.md #3: "Explicit over magical."
"""

import asyncio
import logging
import uuid
from time import perf_counter

from litestar.types import ASGIApp, Receive, Scope, Send
from litestar.types.asgi_types import HTTPScope

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
        http_scope: HTTPScope = scope  # ty: ignore[invalid-assignment]
        qs = http_scope.get("query_string", b"").decode()
        path = f"{http_scope['path']}?{qs}" if qs else http_scope["path"]
        logger.info("[%s] %s %s - started", req_id, http_scope["method"], path)
        start = perf_counter()
        try:
            await app(scope, receive, send)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning("[%s] Connection lost during %s %s: %s", req_id, http_scope["method"], http_scope["path"], e)
        finally:
            elapsed = perf_counter() - start
            logger.info("[%s] %s %s: %.3fs", req_id, http_scope["method"], http_scope["path"], elapsed)

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

        scope["_repos"] = []  # ty: ignore[invalid-key]

        handler = asyncio.create_task(app(scope, receive, send))  # ty: ignore[invalid-argument-type]

        async def watch_disconnect() -> None:
            """Poll receive for client disconnect."""
            while True:
                msg = await receive()
                if msg["type"] == "http.disconnect":
                    for repo in scope.get("_repos", []):
                        try:
                            await repo.cancel_running_query()
                        except Exception:  # noqa: S110
                            pass
                    handler.cancel()
                    return

        watcher = asyncio.create_task(watch_disconnect())

        try:
            await handler
        except asyncio.CancelledError:
            logger.warning("Request cancelled by client disconnect")
        finally:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass

    return middleware


# Dependencies whose presence in a handler's signature indicates a
# "heavy" endpoint that should be short-circuited on HEAD.
_HEAVY_DEPS = frozenset({"source_repo", "feature_repo", "flowline_repo", "catchment_repo", "pygeoapi_client"})


def head_shortcircuit_factory(app: ASGIApp) -> ASGIApp:
    """Short-circuit HEAD requests on heavy endpoints.

    Fires after Litestar's route resolution. If the resolved handler
    injects a repository or pygeoapi_client dependency, the middleware
    validates the ``f=`` query parameter and returns an empty 200
    response without invoking the handler. If ``f=`` is invalid, returns
    400 with problem+json semantics.

    Lightweight handlers (no heavy dependency) pass through so Litestar
    handles HEAD automatically (strips body from GET response).
    """
    from .negotiate import validate_format_param

    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "HEAD":
            await app(scope, receive, send)
            return

        route_handler = scope.get("route_handler")
        if route_handler is None:
            await app(scope, receive, send)
            return

        # Check if the handler uses heavy dependencies
        params = set(route_handler.parsed_fn_signature.parameters.keys())
        if not params & _HEAVY_DEPS:
            await app(scope, receive, send)
            return

        # Validate f= query parameter
        query_string: bytes = scope.get("query_string", b"")
        error = validate_format_param(query_string)
        if error:
            import json as _json

            body = _json.dumps({"type": "about:blank", "title": "Bad Request", "status": 400, "detail": error}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [
                        (b"content-type", b"application/problem+json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        # Short-circuit: return empty 200
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    return middleware
