#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# See the full copyright notice in LICENSE.md
#
"""Network Linked Data Index (NLDI) Python package."""

__version__ = "0.1.0"

import logging

from . import log

NAD83_SRID = 4269

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.WARNING) ## Can be adjusted later