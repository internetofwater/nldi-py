#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

from typing import Union

import shapely
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy import func

from .. import LOGGER, NAD83_SRID
from ..schemas.nhdplus import CatchmentModel
from ..util import url_join
from . import BaseHandler
from .errors import ProviderItemNotFoundError


class CatchmentHandler(BaseHandler):
    def __init__(self, provider_def):
        super().__init__(provider_def)
        self.base_url = provider_def["base_url"]
        self.relative_url = url_join(self.base_url, "linked-data/comid")
        self.id_field = "featureid"
        self.table_model = CatchmentModel

    def query(self, coords: str, asGeoJSON: bool = False) -> Union[dict, int]:
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
        LOGGER.debug(f"{self.__class__.__name__} fetching comid by coordinates: {coords=}")
        with self.session() as session:
            # Retrieve data from database as feature
            point = WKTElement(coords, srid=NAD83_SRID)
            intersects = func.ST_Intersects(CatchmentModel.the_geom, point)
            result = session.filter(intersects).first()

            if result is None:
                raise ProviderItemNotFoundError(f"No comid found for: {coords=}.")

            LOGGER.debug(f"Intersection with {result.featureid}")
            if asGeoJSON:
                return self._sqlalchemy_to_feature(result)
            else:
                return result.featureid

    def _sqlalchemy_to_feature(self, item):
        try:
            shapely_geom = to_shape(item.the_geom)
            geojson_geom = shapely.geometry.mapping(
                shapely_geom
            )  ## TODO: __geo_interface__ instead?  Avoids an import.
            geometry = geojson_geom
        except Exception as e:
            LOGGER.error(f"Error converting geometry to GeoJSON: {e}")
            geometry = None

        navigation = url_join(self.relative_url, item.featureid, "navigation")

        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "identifier": item.featureid,
                "source": "comid",
                # "name": item.name,
                "comid": item.comid,
                "uri": item.uri,
                "reachcode": item.reachcode,
                "measure": item.measure,
                "navigation": navigation,
            },
        }
