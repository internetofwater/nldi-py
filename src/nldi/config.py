# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Application configuration via environment variables."""

import logging
import os


def get_prefix() -> str:
    """Return the URL path prefix for the application."""
    return os.getenv("NLDI_PREFIX", "/api/nldi")


def get_log_level() -> str:
    """Return the configured log level name from NLDI_LOG_LEVEL env var."""
    name = os.getenv("NLDI_LOG_LEVEL", "WARNING").upper()
    if name not in logging.getLevelNamesMapping():
        return "WARNING"
    return name


def get_database_url() -> str:
    """Assemble the database connection URL from component env vars.

    Required: NLDI_DB_HOST, NLDI_DB_NAME, NLDI_DB_USERNAME, NLDI_DB_PASSWORD.
    Optional: NLDI_DB_PORT (default: 5432).
    """
    host = os.getenv("NLDI_DB_HOST")
    name = os.getenv("NLDI_DB_NAME")
    user = os.getenv("NLDI_DB_USERNAME")
    password = os.getenv("NLDI_DB_PASSWORD")
    port = os.getenv("NLDI_DB_PORT", "5432")

    missing = [
        k
        for k, v in {
            "NLDI_DB_HOST": host,
            "NLDI_DB_NAME": name,
            "NLDI_DB_USERNAME": user,
            "NLDI_DB_PASSWORD": password,
        }.items()
        if not v
    ]
    if missing:
        raise RuntimeError(f"Required database env var(s) not set: {', '.join(missing)}")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


def get_base_url() -> str:
    """Return the public-facing base URL from NLDI_BASE_URL env var."""
    url = os.getenv("NLDI_BASE_URL")
    if not url:
        raise RuntimeError("NLDI_BASE_URL environment variable is required but not set.")
    return url
