# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""NLDI database access layer.

Engine singleton and async session provider. The session provider
guarantees rollback+close on error or client disconnect, preventing
zombie connections in the pool.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from ..config import get_database_url

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Return the shared async engine, creating it on first call."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=10,
            pool_timeout=60,
            connect_args={"server_settings": {"statement_timeout": "120000"}},
        )
    return _engine


async def provide_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session with guaranteed cleanup.

    On success the session is committed. On any exception — including
    ``asyncio.CancelledError`` from a client disconnect — the session
    is rolled back. The connection is always returned to the pool.
    """
    async with AsyncSession(get_engine()) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
