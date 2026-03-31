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
    """Return the database connection URL from NLDI_DATABASE_URL env var."""
    url = os.getenv("NLDI_DATABASE_URL")
    if not url:
        raise RuntimeError("NLDI_DATABASE_URL environment variable is required but not set.")
    return url
