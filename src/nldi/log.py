#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#

"""Logging system configuration."""

import logging
import sys
from importlib.metadata import version as lib_ver
from typing import Any, Dict, List

from . import LOGGER


def setup_logger(logging_config: Dict[str, Any]) -> None:
    """
    Set up the logging system.

    Note that this is a legacy function; it is currently set up as a wrapper around
    the more explicit `initialize` function (below).

    :param logging_config: _description_
    :type logging_config: Dict[str, Any]
    """
    # log_format = "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s"
    # date_format = "%Y-%m-%dT%H:%M:%SZ"

    loglevel = logging_config.get("level", logging.INFO)

    if "logfile" in logging_config:
        initialize(LOGGER, level=loglevel, logfile=logging_config["logfile"])
    else:
        initialize(LOGGER, level=loglevel)

    LOGGER.warning("The use of setup_logger is being deprecated; use nldi.log.initialize() instead.")
    return


def initialize(logger: logging.Logger = None, level: str | int = logging.WARNING, logfile=None) -> logging.Logger:
    """
    Initialize the logging system.

    :param logger: logger instance

    :returns: None
    """
    if not logger:
        logger = logging.getLogger()

    if isinstance(level, str):
        # translate to logging level:  "DEBUG" --> logging.DEBUG, etc.
        if level.upper() not in logging._nameToLevel:  ## needed with python 3.10.
            # v3.11 and later introduced logging.getLevelNamesMapping() to provide public access to _nameToLevel
            # TODO: remove call to private var when we can safely assume 3.11 or later
            level = logging.WARNING  # unknown level name; default to WARNING
        else:
            level = logging._nameToLevel[level.upper()]
    if logfile:
        h = logging.handlers.TimedRotatingFileHandler(logfile, when="midnight", interval=1, backupCount=7)
        # If you want to log as JSON, use the following formatter:
        _fmt = dict(
            logger="%(name)s",
            level="%(levelname)s",
            asctime="%(asctime)s",
            location="%(module)s.%(funcName)s#L%(lineno)d",
            message="%(message)s",
        )
        f = logging.Formatter(dumps(_fmt), datefmt="%Y-%m-%dT%H:%M:%S")
        # otherwise, use the same formatter as the StreamHandler below
        ## TODO: JSON-formatted logs as a configurable option?
    else:
        h = logging.StreamHandler(sys.stdout)
        f = logging.Formatter(
            "[%(levelname)s] [%(asctime)s] %(name)s - %(module)s.%(funcName)s#L%(lineno)d: %(message)s"
        )
    h.setLevel(logging.DEBUG)  # << This is the level of the handler, not the logger overall
    h.setFormatter(f)
    logger.addHandler(h)
    logger.setLevel(level)  # << This is the level of the logger, not the handler
    if level == logging.DEBUG:
        # Silence some of the more verbose loggers
        keys_to_shush = [k for k in logging.root.manager.loggerDict if k.startswith("numba")]
        keys_to_shush.extend([k for k in logging.root.manager.loggerDict if k.startswith("fiona")])
        keys_to_shush.extend([k for k in logging.root.manager.loggerDict if k.startswith("rasterio")])
        for k in keys_to_shush:
            logging.getLogger(k).propagate = False
            # OR do this instead  if you want to see warnings in the root logger instead of blocking alltogether
            # logging.getLogger(k).setLevel(logging.WARNING)
    return logger


def versions(mlist: List[str] | None = None, logger=None, level=logging.INFO) -> None:
    """
    Print the versions of the modules in the list mlist.

    :param mlist: list of module names

    :returns: None
    """
    if not logger:
        logger = logging.getLogger()
    _v = sys.version.replace("\n", "")
    logger.log(level, f"Python: {_v}")
    if not mlist:
        mlist = ["sqlalchemy", "flask", "pydantic"]
        # TODO: customize this list for the specific project.
        # NOTE: this is just the default list... the caller can specifiy a different list if desired.
    vlist = []
    for m in mlist:
        try:
            vlist.append(f"{m}:{lib_ver(m)}")
        except ModuleNotFoundError:
            vlist.append(f"{m}:not installed")
    logger.log(level, " // ".join(vlist))
