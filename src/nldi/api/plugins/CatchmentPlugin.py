#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# See the full copyright notice in LICENSE.md


"""Catchment Plugin"""

import json
from typing import Any, Dict, List, Union

import sqlalchemy
from geoalchemy2 import WKTElement

from ... import LOGGER, NAD83_SRID, util
from ...schemas.nhdplus import CatchmentModel
from .APIPlugin import APIPlugin


class CatchmentPlugin(APIPlugin):
    """
    NHD Catchment Plugin

    This plugin provides a mechanism to query the NHDPlus catchment data.

    A catchment is the land surface area flowing directly into an NHDPlus
    feature.  This plugin provides methods to find NHD Catchments either by
    its COMID or by a point geometry.

    """

    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        super().__init__(name, **kwargs)
        self.table_model = CatchmentModel
        self.geom_field = CatchmentModel.the_geom
        self.id_field = CatchmentModel.featureid

    @property
    def relative_url(self):
        """
        Get the relative URL used to construct properties of the returned GeoJSON.

        Some properties of the returned feature are URLs which indicate subsequent services
        that can be used to retrieve additional information about the feature (e.g. navigation).
        This property is used as the base of those URLs, as they are all relative to this
        plugin's base URL.

        The relative url is dependent on the parent's (i.e. the ``API``) base URL.  For un-registered
        plugins, a default URL is returned.

        :return: The relative URL for this plugin
        :rtype: str
        """
        if self.is_registered:
            return util.url_join(self.parent.base_url, "linked-data/comid")
        else:
            LOGGER.info("Attempt to get relative_url from an unregistered plugin.")
            return "/linked-data/comid"

    def get_by_id(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a catchment by its COMID.

        The featureid is the unique COMID identifier for a Catchment in the
        NHDPlus database. The returned data is a GeoJSON feature (either polygon
        or multipolygon) as a python dictionary.

        :param id: comid of the catchment
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
        Perform a spatial query against the NHDPlus/catchmentsp table.

        The spatial search uses a point geometry to find the catchment, which is passed in as
        the ``coords`` parameter. The point geometry is expected to be in the form of a WKT
        (in the form 'POINT(longitude latitude)')in NAD83 (EPSG:4269) coordinates.  We do
        not parse this string, but pass it directly to ``geoalchemy``'s ``WKTElement`` object
        for interpretation. Malformed point geometries will raise an exception.

        :param coords: WKT of point element
        :param asGeoJSON: return data as GeoJSON feature (default: False)
        :returns: dict of 0..n GeoJSON features (if asGeoJSON is True) else the
            ``featureid`` of the matching catchment.
        """
        LOGGER.debug(f"{self.__class__.__name__} GET Catchment by Coordinates: {coords}")

        with self.session() as session:
            geojson = sqlalchemy.func.ST_AsGeoJSON(CatchmentModel.the_geom).label("geojson")
            # Retrieve data from database as feature
            point = WKTElement(coords, srid=NAD83_SRID)
            # LOGGER.debug(f"Using this point for selection: {point}")
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
