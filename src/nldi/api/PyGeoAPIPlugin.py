#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
PyGeoAPI Plugin

This plugin provides a mechanism for proxying requests to a PyGeoAPI
instance running elsewhere.  This is a base class for other plugins
to inherit from.

"""
import json
from typing import Any, Dict, List

import httpx

from .. import LOGGER
from .err import ProviderQueryError
from .BasePlugin import APIPlugin

class PyGeoAPIPlugin(APIPlugin):
    DEFAULT_PYGEOAPI_URL = "https://labs-beta.waterdata.usgs.gov/api/nldi/pygeoapi"
    HTTP_TIMEOUT = 20 # seconds
    DEFAULT_PROPS = {
        "identifier": "",
        "navigation": "",
        "measure": "",
        "reachcode": "",
        "name": "",
        "source": "provided",
        "sourceName": "Provided via API call",
        "comid": "",
        "type": "point",
        "uri": "",
    }
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    @property
    def pygeoapi_url(self) -> str:
        if self.is_registered:
            return self.parent.config.get("pygeoapi_url", self.DEFAULT_PYGEOAPI_URL)
        else:
            LOGGER.error("Attempt to get pygeoapi_url from an unregistered plugin.")
            return self.DEFAULT_PYGEOAPI_URL

    @classmethod
    def _post_to_external_service(cls, url: str, data: dict = {}) -> dict:
        LOGGER.debug(f"{__class__.__name__} Sending POST request to: {url}")
        try:
            with httpx.Client() as client:
                r = client.post(url, data=json.dumps(data), timeout=cls.HTTP_TIMEOUT).raise_for_status()
                response = r.json()
        except httpx.HTTPStatusError as err:
            LOGGER.error(f"HTTP error: {err}")
            raise ProviderQueryError from err
        except json.JSONDecodeError as err:
            LOGGER.error(f"JSON decode error: {err}")
            raise ProviderQueryError from err
        return response
