#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# See the full copyright notice in LICENSE.md

"""
PyGeoAPI Plugin

"""

import json
from typing import Any, Dict, List

import httpx

from ... import LOGGER
from ..err import ProviderQueryError
from .APIPlugin import APIPlugin


class PyGeoAPIPlugin(APIPlugin):
    """
    Provides a mechanism for proxying requests to a PyGeoAPI instance running elsewhere.

    This is a base class for other plugins, notably the ``HydroLocationPlugin`` and
    ``SplitCatchmentPlugin``.  This class provides a single source for common utility functions
    and constants used by those subclasses.
    """

    DEFAULT_PYGEOAPI_URL = "https://labs-beta.waterdata.usgs.gov/api/nldi/pygeoapi"
    HTTP_TIMEOUT = 20  # seconds
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

    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        super().__init__(name, **kwargs)

    @property
    def pygeoapi_url(self) -> str:
        """
        Get the URL of the PyGeoAPI instance to which requests will be sent.

        The parent API is configurable, and that configuration includes a custom URL
        for this value.  If left unconfigured, or if this plugin is running in
        "unregistered" state (e.g. for testing purposes), this string will default
        to a known URL.

        :return: The URL of the PyGeoAPI service.
        :rtype: str
        """
        if self.is_registered:
            return self.parent.config.get("pygeoapi_url", self.DEFAULT_PYGEOAPI_URL)
        else:
            LOGGER.info("Attempt to get pygeoapi_url from an unregistered plugin.")
            return self.DEFAULT_PYGEOAPI_URL

    @classmethod
    def _post_to_external_service(cls, url: str, data: dict = {}, timeout: int = 0) -> dict:
        _to = timeout if timeout > 0 else cls.HTTP_TIMEOUT
        LOGGER.debug(f"{__class__.__name__} Sending POST (timeout={_to}) to: {url}")
        try:
            with httpx.Client() as client:
                r = client.post(url, data=json.dumps(data), timeout=_to).raise_for_status()
                response = r.json()
        except httpx.HTTPStatusError as err:  # pragma: no cover
            LOGGER.error(f"HTTP error: {err}")
            raise ProviderQueryError from err
        except json.JSONDecodeError as err:  # pragma: no cover
            LOGGER.error(f"JSON decode error: {err}")
            raise ProviderQueryError from err
        return response
