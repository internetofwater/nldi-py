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

from typing import Any, Dict, List

import httpx
import shapely
import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER, util
from ..schemas.nhdplus import FlowlineModel
from ..schemas.nldi_data import CrawlerSourceModel
from .CatchmentPlugin import CatchmentPlugin
from .err import ProviderGenericError, ProviderQueryError
from .PyGeoAPIPlugin import PyGeoAPIPlugin


class HydroLocationPlugin(PyGeoAPIPlugin):
    @property
    def catchment_lookup(self):
        """
        Return a catchment lookup plugin.

        This is a property that returns a CatchmentPlugin instance.  If the plugin is not registered,
        it will create a new instance with a default name and database connection URL.  If this plugin
        is propertly registered with the API, it will return the catchment plugin instance that is
        registered with the parent.
        """
        if self.is_registered and "Catchment" in self.parent.plugins:
            return self.parent.plugins["Catchment"]
        else:
            LOGGER.warning("Attempt to get catchment_lookup from an unregistered plugin.")
            return CatchmentPlugin("Catchment-From-HydroLocation", db_connect_url=self._db_connect_url)

    @property
    def flowtrace_service_endpoint(self) -> str:
        """Return the fully qualified URL for the flowtrace service endpoint."""
        return util.url_join(self.pygeoapi_url, "processes", "nldi-flowtrace", "execution")

    def get_by_coords(self, coords: str) -> dict:
        """
        Get a hydrolocation by coordinates.



        :param coords: _description_
        :type coords: str
        :raises ProviderQueryError: _description_
        :raises KeyError: _description_
        :return: _description_
        :rtype: dict
        """
        LOGGER.debug(f"{__class__.__name__} get_by_coords: {coords}")
        point = shapely.wkt.loads(coords)
        request_payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": str(point.x)},
                {"id": "lat", "type": "text/plain", "value": str(point.y)},
                {"id": "direction", "type": "text/plain", "value": "none"},
            ]
        }

        response = self._post_to_external_service(self.flowtrace_service_endpoint, data=request_payload)
        [lon, lat] = response["features"][0]["properties"]["intersection_point"]  # noqa
        wkt_geom = f"POINT({lon} {lat})"
        LOGGER.debug(f"Intersection point from flowtrace service: {wkt_geom}")

        try:
            nhdplus_comid = self.catchment_lookup.get_by_coords(wkt_geom)
        except KeyError as err:
            LOGGER.error(f"Error querying catchment lookup: {err}")
            raise ProviderQueryError from err
        LOGGER.debug("Found COMID: {nhdplus_comid} for the catchment at {coords}")
        nav_url = util.url_join(self.base_url, "linked-data", "comid", nhdplus_comid, "navigation")

        LOGGER.debug(f"Getting measure for {nhdplus_comid}")
        measure = (
            FlowlineModel.fmeasure
            + (
                1
                - sqlalchemy.func.ST_LineLocatePoint(
                    FlowlineModel.shape, sqlalchemy.func.ST_GeomFromText(wkt_geom, 4269)
                )  # noqa
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

        _return_feature_collection = {
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
                    "properties": self.DEFAULT_PROPS,
                },
            ],
        }
        return _return_feature_collection
