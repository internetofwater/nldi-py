#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import json
from typing import Any, Dict, List, Union

import sqlalchemy
from geoalchemy2 import WKTElement

from ... import LOGGER, NAD83_SRID, util
from ...schemas.nhdplus import CatchmentModel
from .APIPlugin import APIPlugin


class CatchmentPlugin(APIPlugin):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.table_model = CatchmentModel
        self.geom_field = CatchmentModel.the_geom
        self.id_field = CatchmentModel.featureid

    @property
    def relative_url(self):
        if self.is_registered:
            return util.url_join(self.parent.base_url, "linked-data/comid")
        else:
            LOGGER.warning("Attempt to get relative_url from an unregistered plugin.")
            return "/linked-data/comid"

    def get_by_id(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a catchment by its featureid.

        The featureid is the unique COMID identifier for a catchment in the NHDPlus database.
        The returned data is a GeoJSON feature as a python dictionary.

        :param id: featureid of the catchment
        :returns: dict of GeoJSON feature
        """
        LOGGER.debug(f"{self.__class__.__name__} GET Catchment by ID: {id}")
        with self.session() as session:
            q = self.query(session)
            item = q.where(self.id_field == id).first()
            if item is None:
                raise KeyError(f"No such catchment found: featureid={id}.")
        return self._sqlalchemy_to_feature(item)

    def get_by_coords(self, coords: str, as_feature: bool = False) -> Union[dict, int]:
        """
        Perform a spatial query against the nhdplus/catchmentsp table.

        The spatial search uses a point geometry to find the catchment, which is passed in as
        the ``coords`` parameter. The point geometry is expected to be in the form of a WKT
        (in the form 'POINT(longitude latitude)')in NAD83 (EPSG:4269) coordinates.  We do
        not parse this string, but pass it directly to ``geoalchemy``'s ``WKTElement`` object
        for interpretation.

        :param coords: WKT of point element
        :param asGeoJSON: return data as GeoJSON feature (default: False)
        :returns: dict of 0..n GeoJSON features (if asGeoJSON is True) else the ``featureid`` of the matching catchment.
        """
        LOGGER.debug(f"{self.__class__.__name__} GET Catchment by Coordinates: {coords}")

        with self.session() as session:
            geojson = sqlalchemy.func.ST_AsGeoJSON(CatchmentModel.the_geom).label("geojson")
            # Retrieve data from database as feature
            point = WKTElement(coords, srid=NAD83_SRID)
            LOGGER.debug(f"Using this point for selection: {point}")
            intersects = sqlalchemy.func.ST_Intersects(CatchmentModel.the_geom, point)
            r = session.query(CatchmentModel, geojson).where(intersects).first()
            ## Setting up the query ^^^^^^^^^^^^^^^ like this means that r is a tuple of (CatchmentModel, GeoJSON_string).
            # This will be important later when it comes time to unpack.
            if r is None:
                raise KeyError
        if as_feature:
            return self._sqlalchemy_to_feature(r)
        else:
            (item, _) = r
            return item.featureid

    def _sqlalchemy_to_feature(self, sql_row):
        item, geojson = sql_row
        navigation_link = util.url_join(self.relative_url, item.featureid, "navigation")
        return {
            "type": "Feature",
            "geometry": json.loads(sql_row.geojson),
            "properties": {
                "identifier": item.featureid,
                "source": "comid",
                ## TODO:  Find out what these fields are for and if they are needed.
                # "name": item.name,
                # "comid": item.comid,
                # "uri": item.uri,
                # "reachcode": item.reachcode,
                # "measure": item.measure,
                "navigation": navigation_link,
            },
        }
