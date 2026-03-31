# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Application configuration via environment variables."""

import logging
import os


def get_prefix() -> str:
    """Return the URL path prefix for the application."""
    return os.getenv("NLDI_PREFIX", "/api/nldi")


def get_log_level() -> int:
    """Return the configured log level from NLDI_LOG_LEVEL env var."""
    name = os.getenv("NLDI_LOG_LEVEL", "WARNING").upper()
    return logging.getLevelNamesMapping().get(name, logging.WARNING)
