# =================================================================
#
# Author: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

"""Logging system"""

import logging
import sys
from importlib.metadata import version as lib_ver
from typing import Any, Dict, List


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


def initialize(logger: logging.Logger, level: str | int = logging.WARNING, logfile=None) -> logging.Logger:
    """
    Initialize the logging system

    :param logger: logger instance

    :returns: None
    """
    if isinstance(level, str):
        # translate to logging level:  "DEBUG" --> logging.DEBUG, etc.
        if level.upper() not in logging.getLevelNamesMapping():
            # unknown level name; default to WARNING
            level = logging.WARNING
        else:
            level = logging.getLevelNamesMapping()[level.upper()]
    if logfile:
        h = logging.handlers.TimedRotatingFileHandler(logfile, when="midnight", interval=1, backupCount=7)
        # If you want to log as JSON, use the following formatter:
        f = logging.Formatter(
            '{"level": "%(levelname)s", "asctime": "%(asctime)s",  "location": "%(module)s.%(funcName)s#L%(lineno)d", "message": "%(message)s"},'
        )
        # otherwise, use the same formatter as below:
        # f = logging.Formatter("[%(levelname)s] [%(asctime)s] %(name)s - %(module)s.%(funcName)s#L%(lineno)d: %(message)s")
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
    return logger


def versions(mlist: List[str] | None = None, logger=None, level=logging.DEBUG) -> None:
    """
    Print the versions of the modules in the list l

    :param l: list of module names

    :returns: None
    """
    if not logger:
        logger = logging.getLogger("nldi")
    logger.log(level, f"Python: {sys.version.replace('\n', '')}")
    if not mlist:
        mlist = ["sqlalchemy", "flask", "pydantic"]
    for m in mlist:
        try:
            logger.log(level, f"{m} : {lib_ver(m)}")
        except ModuleNotFoundError:
            logger.log(level, f"{m} : --")
