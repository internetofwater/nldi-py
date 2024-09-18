#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
Split Catchment Plugin

This plugin provides a mechanism for proxying requests to a PyGeoAPI
instance running elsewhere, and uses the result of that query to compose
a response on the NLDI service.

"""

from typing import Any, Dict, List

import httpx
import shapely
import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from ... import LOGGER, util
from ..err import ProviderGenericError, ProviderQueryError
from .PyGeoAPIPlugin import PyGeoAPIPlugin


class SplitCatchmentPlugin(PyGeoAPIPlugin):
    @property
    def splitcatchment_service_endpoint(self) -> str:
        return util.url_join(self.pygeoapi_url, "processes", "nldi-splitcatchment", "execution")

    def get_by_coords(self, coords: str) -> Dict[str, Any]:
        """
        query split catchment

        :param coords: WKT of point element

        :returns: GeoJSON features
        """
        LOGGER.debug(f"{__class__.__name__} get_by_coords: {coords}")
        point = shapely.wkt.loads(coords)
        request_payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": str(point.x)},
                {"id": "lat", "type": "text/plain", "value": str(point.y)},
                {"id": "upstream", "type": "text/plain", "value": "true"},
            ]
        }

        url = util.url_join(self.pygeoapi_url, "processes/nldi-splitcatchment/execution")  # noqa
        response = self._post_to_external_service(
            self.splitcatchment_service_endpoint,
            data=request_payload,
            timeout=2 * self.HTTP_TIMEOUT,  ## give the split algorithm a bit more time to work.
        )

        # Search for feature with id "mergedCatchment" or "drainageBasin"
        _to_return = None
        for feature in response["features"]:
            if feature["id"] == "mergedCatchment" or feature["id"] == "drainageBasin":
                # The ID changes from "mergedCatchment" to "drainageBasin" with this commit in Aug, 2024:
                # https://code.usgs.gov/wma/nhgf/toolsteam/nldi-flowtools/-/commit/08b4042cbfe34d2c22dfac83120c0629d9ad444f
                # Trapping both of these possible IDs now to handle the case when that change makes it to production.
                feature.pop("id")
                _to_return = feature

        return _to_return  # caller is expecting an iterable
        # previous versions yielded the return value here, allowing caller to loop over a generator producing
        # just the single value. Returning the single feature instead represents a breaking change -- caller must
        # make their own list if they need this feature in that form.
