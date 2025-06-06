#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Configurator."""

import logging
import os
import pathlib
from functools import lru_cache

from ._yaml import load_yaml
from .base import MasterConfig


def get_config() -> MasterConfig:
    if os.getenv("NLDI_CONFIG"):
        __configfile = pathlib.Path(os.getenv("NLDI_CONFIG")).resolve()
    else:
        __configfile = pathlib.Path("./nldi.yml").resolve()

    logging.info(f"Attempting to read config file from {__configfile}")
    if __configfile.exists():
        _config = MasterConfig.from_yaml(__configfile)
    else:
        raise RuntimeError(f"Config file {__configfile} does not exist.")

    return _config
