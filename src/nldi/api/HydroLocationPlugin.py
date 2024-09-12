#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
HydroLocation Plugin


This plugin provides a mechanism for proxying requests to a PyGeoAPI
instance running elsewhere, and uses the result of that query to further
search within the NLDI database.

"""


from contextlib import contextmanager
from typing import Any, Dict, List

import httpx
import sqlalchemy
from sqlalchemy.engine import URL as DB_URL
import shapely
from .. import LOGGER
from ..schemas.nldi_data import CrawlerSourceModel
from .PyGeoAPIPlugin import PyGeoAPIPlugin


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


class HydroLocationPlugin(PyGeoAPIPlugin):

    def get_by_coords(self, coords: str) -> dict:
        LOGGER.debug(f"{__class__.__name__} get_by_coords: {coords}")
        point = shapely.wkt.loads(coords)
        request_payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": point.x},
                {"id": "lat", "type": "text/plain", "value": point.y},
                {"id": "direction", "type": "text/plain", "value": "none"},
            ]
        }
        url = util.url_join(self.pygeoapi_url, "processes", "nldi-flowtrace", "execution")
        response = self._post_to_external_service(url, data=request_payload)

        [lon, lat] = response["features"][0]["properties"]["intersection_point"]  # noqa
        wkt_geom = f"POINT({lon} {lat})"


        nhdplus_comid = self.catchment_lookup.query(wkt_geom)


        nav_url = url_join(self.base_url, "linked-data", "comid", nhdplus_comid, "navigation")

        LOGGER.debug(f"Getting measure for {nhdplus_comid}")
        measure = (
            FlowlineModel.fmeasure
            + (
                1 - func.ST_LineLocatePoint(FlowlineModel.shape, func.ST_GeomFromText(wkt_geom, 4269))  # noqa
            )
            * (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
        ).label("measure")

        with self.session() as session:
            result = (
                session.query(measure, FlowlineModel.reachcode)
                .filter(FlowlineModel.nhdplus_comid == nhdplus_comid)
                .first()
            )

            if result is None:
                raise KeyError(f"No measure found for: {coords}.")

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

