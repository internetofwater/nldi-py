#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# See the full copyright notice in LICENSE.md


"""
Split Catchment Plugin

"""

from typing import Any, Dict, List

from geomet import wkt
import httpx
# import shapely
import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from ... import LOGGER, util
from ..err import ProviderGenericError, ProviderQueryError
from .PyGeoAPIPlugin import PyGeoAPIPlugin


class SplitCatchmentPlugin(PyGeoAPIPlugin):
    """
    Split Catchment Plugin

    This plugin provides a mechanism for proxying requests to the PyGeoAPI service offering a
    split catchment algorithm (running elsewhere).  This plugin is little more than a proxy
    to that service, and adds no additional business logic.

    The nature of this plugin is such that it does not make sense to query by ID. ``get_by_id()``
    is not implemented in this plugin. The coordinate lookup in ``get_by_coords()`` is the primary
    method for this plugin.

    Note that the external split catchment service can take a long time to respond.  The timeout
    for this service is set to 2x the default timeout for PyGeoAPI service calls. This is to allow
    the split catchment algorithm to complete its work before the timeout is reached.
    """

    @property
    def splitcatchment_service_endpoint(self) -> str:
        """Return the url for the split catchment service endpoint."""
        return util.url_join(self.pygeoapi_url, "processes", "nldi-splitcatchment", "execution")

    def get_by_coords(self, coords: str) -> Dict[str, Any]:
        """
        query split catchment

        :param coords: WKT of point element
        :type coords: str
        :returns: GeoJSON features
        """
        LOGGER.debug(f"{__class__.__name__} get_by_coords: {coords}")
        point = wkt.loads(coords)
        # point = shapely.wkt.loads(coords)
        request_payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": str(point['coordinates'][0])},
                {"id": "lat", "type": "text/plain", "value": str(point['coordinates'][1])},
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
