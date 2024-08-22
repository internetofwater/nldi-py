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

import io
import logging
import pathlib
from copy import deepcopy
from typing import Union

from pygeoapi.util import get_base_url

from . import LOGGER, util
from .lookup.base import ProviderQueryError
from .lookup.source import CrawlerSourceLookup


def align_crawler_sources(cfg_file: Union[pathlib.Path, io.TextIOWrapper]) -> bool:
    """
    Align Crawler Source from the configuration file

    :param cfg_file: Configuration Path instance
    :type cfg_file: Union[pathlib.Path, io.TextIOWrapper]
    :return: Success/Failure of alignment
    :rtype: bool
    """
    LOGGER.debug("Aligning sources from config file.")
    config = util.load_yaml(cfg_file)
    if not config:
        LOGGER.error("Unable to load configuration file.")
        return False

    if not config.get("sources"):
        LOGGER.debug("No sources to align with, continuing")
        return True

    provider_def = {
        "database": deepcopy(config["server"]["data"]),
        "base_url": get_base_url(config),
    }

    LOGGER.debug("Aligning configuration with crawler source table")
    try:
        crawler_source = CrawlerSourceLookup(provider_def)
        crawler_source.align_sources(config["sources"])
    except ProviderQueryError:
        LOGGER.error("Provider Query Error -- Do you have permissions to update Crawler source table?")
        return False

    return True
