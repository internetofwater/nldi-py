# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Application configuration via environment variables."""

import logging
import os


def get_prefix() -> str:
    return os.getenv("NLDI_PREFIX", "/api/nldi")


def get_log_level() -> int:
    name = os.getenv("NLDI_LOG_LEVEL", "WARNING").upper()
    return logging.getLevelNamesMapping().get(name, logging.WARNING)
