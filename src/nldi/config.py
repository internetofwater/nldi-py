#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

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
from copy import deepcopy

import io
import logging
import pathlib
from collections import UserDict
from os import environ as ENV  # noqa: N812
from typing import Union

from pygeoapi.util import get_base_url  ## TODO: can we drop this dependency?
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


class Configuration(UserDict):
    # TODO:  This class refactors current behavior, which is to read config from a YAML file
    #         or open IO Stream and instantiate dictionary.  Is it useful to also be able to
    #         ingest JSON or other formats.  If so, perhaps class methods like ``.from_json()``
    #         ``from_yaml()`` or ``.from_dict()`` would be useful.  At some point, this should
    #         be refactored to use a schema for validation (i.e. Pydantic model).
    def __init__(self, cfg_src: Union[pathlib.Path, str, io.TextIOWrapper]):
        if cfg_src is None:
            raise ValueError("No configuration specified.")
        LOGGER.debug("Loading configuration file.")

        if LOGGER.level == logging.DEBUG:
            ## IF in debug mode, mock/force the os environment variables. Will not overwrite if key already present in environ.
            # We need these environment variables to be set, as they are substituted/inserted in the config file. If not set,
            # the config file will not load properly.
            for k, v in dict(
                #NLDI_PATH="/api/nldi",
                NLDI_URL="http://localhost:8081/",
                NLDI_DB_HOST="172.17.0.2",  # This is the IP address for the Docker container
                NLDI_DB_PORT="5432",
                NLDI_DB_NAME="nldi",
                NLDI_DB_USERNAME="nldi",
                NLDI_DB_PASSWORD="changeMe",  # noqa: S106
                PYGEOAPI_URL="https://labs.waterdata.usgs.gov/api/nldi/pygeoapi/",
            ).items():
                if k not in ENV:
                    ENV[k] = v

        self.data = util.load_yaml(cfg_src)
        self.data["base_url"] = utils.url_join(self.data["server"]["url"], "")

        if isinstance(cfg_src, io.TextIOWrapper):
            self._config_src = "<stream>"
        else:
            self._config_src = str(cfg_src)

    @property
    def config_source(self) -> str:
        return self._config_src

