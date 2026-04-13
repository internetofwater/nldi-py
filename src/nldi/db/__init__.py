# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""NLDI database access layer.

Engine singleton and async session provider. The session provider
guarantees rollback+close on error or client disconnect, preventing
zombie connections in the pool.
"""

import asyncio
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from ..config import get_database_url


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return the shared async engine, creating it on first call."""
    return create_async_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=30,
        pool_timeout=60,
        connect_args={
            "server_settings": {
                "statement_timeout": "120s",
                "idle_in_transaction_session_timeout": "30s",
            }
        },
    )


@lru_cache(maxsize=1)
def get_cancel_engine() -> AsyncEngine:
    """Return a dedicated single-connection engine for pg_cancel_backend calls.

    Isolated from the main pool so cancel calls are never blocked by the
    pool exhaustion they are trying to resolve.
    """
    return create_async_engine(get_database_url(), pool_size=1, max_overflow=0)


async def provide_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session with guaranteed cleanup.

    On cancellation (client disconnect), the session connection may be in an
    unknown state after pg_cancel_backend fires. We invalidate it so the pool
    discards it and decrements checked_out, rather than attempting a clean
    return that may silently fail.
    """
    session = AsyncSession(get_engine())
    try:
        yield session
    except asyncio.CancelledError:
        asyncio.ensure_future(session.invalidate())
        raise
    finally:
        asyncio.ensure_future(session.close())
