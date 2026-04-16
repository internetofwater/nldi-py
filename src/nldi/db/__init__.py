# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""NLDI database access layer.

Engine singleton and async session provider. The session provider
guarantees rollback+close on error or client disconnect, preventing
zombie connections in the pool.
"""

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
            "options": "-c statement_timeout=120000 -c idle_in_transaction_session_timeout=30000"
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

    SQLAlchemy's AsyncSession.__aexit__ handles cancellation-safe close
    internally via asyncio.shield. We let it do that and stay out of the way.
    """
    async with AsyncSession(get_engine()) as session:
        yield session
