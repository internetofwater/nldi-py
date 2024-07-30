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

import json
import logging
from requests import Session as HTTPSession
from shapely import wkt
from sqlalchemy import func
from sqlalchemy.orm import Session

from nldi.lookup.base import BaseLookup, ProviderItemNotFoundError, ProviderConnectionError, ProviderQueryError
from nldi.schemas.nhdplus import FlowlineModel
from nldi.util import url_join

LOGGER = logging.getLogger(__name__)

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


class PygeoapiLookup(BaseLookup):
    def __init__(self, provider_def):
        """
        Pygeoapi Lookup Class constructor

        :param provider_def: provider definitions from yml nldi-config.
                             data, id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor

        :returns: nldi.lookup.pygeoapi.PygeoapiLookip
        """
        LOGGER.debug("Initialising Pygeoapi Lookup.")
        self.catchment_lookup = provider_def["catchment_lookup"]
        self.pygeoapi_url = provider_def["pygeoapi_url"]
        self.base_url = provider_def["base_url"]
        self.http = HTTPSession()

        super().__init__(provider_def)

    def get_hydrolocation(self, coords: str) -> dict:
        """
        query by hydrolocation

        :param coords: WKT of point element

        :returns: dict of 2 GeoJSON features
        """
        LOGGER.debug(f"Extracting geom from WKT: {coords}")
        point = wkt.loads(coords)
        data = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": point.x},
                {"id": "lat", "type": "text/plain", "value": point.y},
                {"id": "direction", "type": "text/plain", "value": "none"},
            ]
        }

        LOGGER.debug("Making OGC API - Processes request")
        url = url_join(self.pygeoapi_url, "processes/nldi-flowtrace/execution")
        response = self._get_response(url, data=data)

        LOGGER.debug("Getting feature intersection")
        [lon, lat] = response["features"][0]["properties"]["intersection_point"]  # noqa
        wkt_geom = f"POINT({lon} {lat})"
        nhdplus_comid = self.catchment_lookup.query(wkt_geom)
        nav_url = url_join(self.base_url, "linked-data/comid", nhdplus_comid, "navigation")

        LOGGER.debug(f"Getting measure for {nhdplus_comid}")
        measure = (
            FlowlineModel.fmeasure
            + (
                1 - func.ST_LineLocatePoint(FlowlineModel.shape, func.ST_GeomFromText(wkt_geom, 4269))  # noqa
            )
            * (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
        ).label("measure")
        with Session(self._engine) as session:
            result = (
                session.query(measure, FlowlineModel.reachcode)
                .filter(FlowlineModel.nhdplus_comid == nhdplus_comid)
                .first()
            )

            if result is None:
                msg = f"No measure found for: {coords}."
                raise ProviderItemNotFoundError(msg)

            computed_measure = result.measure
            computed_reach = result.reachcode

        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "identifier": "",
                        "navigation": nav_url,
                        "measure": computed_measure,
                        "reachcode": computed_reach,
                        "name": "",
                        "source": "indexed",
                        "sourceName": "Automatically indexed by the NLDI",
                        "comid": nhdplus_comid,
                        "type": "hydrolocation",
                        "uri": "",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [point.x, point.y]},
                    "properties": DEFAULT_PROPS,
                },
            ],
        }
        return fc

    def get_split_catchment(self, coords: str) -> dict:
        """
        query split catchment

        :param coords: WKT of point element

        :returns: GeoJSON features
        """
        LOGGER.debug(f"Extracting geom from WKT: {coords}")
        point = wkt.loads(coords)
        data = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": f"{point.x}"},
                {"id": "lat", "type": "text/plain", "value": f"{point.y}"},
                {"id": "upstream", "type": "text/plain", "value": "true"},
            ]
        }

        LOGGER.debug("Making OGC API - Processes request")
        url = url_join(self.pygeoapi_url, "processes/nldi-splitcatchment/execution")  # noqa
        response = self._get_response(url, data=data)

        for feature in response["features"]:
            if feature["id"] == "mergedCatchment":
                feature.pop("id")
                yield feature

    def _get_response(self, url: str, data: dict = {}) -> dict:
        """
        Private function: Get pygeoapi response

        :param url: request url
        :param data: POST body

        :returns: pygeoapi response
        """

        r = self.http.post(url, json=data)

        if not r.ok:
            LOGGER.error("Bad http response code")
            raise ProviderConnectionError("Bad http response code")

        try:
            response = r.json()
        except json.JSONDecodeError as err:
            LOGGER.error("JSON decode error")
            raise ProviderQueryError(err)

        return response
