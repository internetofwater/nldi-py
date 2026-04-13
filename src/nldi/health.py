# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Health check utilities for dependent services."""

import logging
import os

import httpx
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from . import __version__
from .config import get_database_url

logger = logging.getLogger(__name__)


async def check_db() -> dict:
    """Check database connectivity. Returns sanitized status and pool stats."""
    host = os.getenv("NLDI_DB_HOST", "unknown")
    # Sanitize: strip hostname, keep rest of FQDN
    sanitized_host = ".".join(host.split(".")[1:]) if "." in host else host
    try:
        url = get_database_url()
        engine = create_async_engine(url, connect_args={"connect_timeout": 3})
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        result: dict = {"name": "db", "cfg": sanitized_host, "status": "online"}
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
        return {"name": "db", "cfg": sanitized_host, "status": "offline", "msg": str(e)}

    # Pool stats from the shared engine (not the throwaway health check engine)
    try:
        from .db import get_engine

        pool = get_engine().pool
        result["pool"] = {
            "size": pool.size(),  # ty: ignore[unresolved-attribute]
            "checked_in": pool.checkedin(),  # ty: ignore[unresolved-attribute]
            "checked_out": pool.checkedout(),  # ty: ignore[unresolved-attribute]
            "overflow": pool.overflow(),  # ty: ignore[unresolved-attribute]
        }
    except Exception:  # noqa: S110
        pass  # Engine not initialized (e.g., no DB env vars)

    return result


async def check_pygeoapi() -> dict:
    """Check pygeoapi service reachability."""
    url = os.getenv("PYGEOAPI_URL", "")
    if not url:
        return {"name": "pygeoapi", "cfg": "not configured", "status": "n/a"}
    try:
        async with httpx.AsyncClient(verify=False) as client:  # noqa: S501
            r = await client.get(f"{url.rstrip('/')}/processes?f=json", timeout=5)
        status = "online" if r.status_code == 200 else "offline"
        return {"name": "pygeoapi", "cfg": url, "status": status}
    except Exception as e:
        logger.warning("pygeoapi health check failed: %s", e)
        return {"name": "pygeoapi", "cfg": url, "status": "offline", "msg": str(e)}


async def health_status() -> dict:
    """Full health check for all services."""
    return {
        "server": {"name": f"NLDI {__version__}", "status": "online"},
        "db": await check_db(),
        "pygeoapi": await check_pygeoapi(),
    }
