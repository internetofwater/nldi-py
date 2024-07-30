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

from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement
import shapely
from sqlalchemy import func
from typing import Union

from nldi.lookup.base import BaseLookup, ProviderItemNotFoundError
from nldi.schemas.nhdplus import CatchmentModel
from nldi.util import url_join

from .. import LOGGER


class CatchmentLookup(BaseLookup):
    def __init__(self, provider_def):
        """
        CatchmentLookup Class constructor

        :param provider_def: provider definitions from yml nldi-config.
                             data, id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor

        :returns: nldi.lookup.catchment.CatchmentLookup
        """
        LOGGER.debug("Initialising Catchment Lookup.")
        super().__init__(provider_def)
        self.id_field = "featureid"
        self.table_model = CatchmentModel

    def query(self, coords: str, asGeoJSON: bool = False) -> Union[dict, int]:
        """
        query the lookup

        :returns: dict of 0..n GeoJSON features or coverage data
        """
        LOGGER.debug(f"Fetching comid of: {coords}")
        with self.session() as session:
            # Retrieve data from database as feature
            point = WKTElement(coords, srid=4269)
            intersects = func.ST_Intersects(CatchmentModel.the_geom, point)
            result = session.filter(intersects).first()

            if result is None:
                msg = f"No comid found for: {coords}."
                raise ProviderItemNotFoundError(msg)

            LOGGER.debug(f"Intersection with {result.featureid}")
            if asGeoJSON:
                item = self._sqlalchemy_to_feature(result)
                return item
            else:
                return result.featureid

    def _sqlalchemy_to_feature(self, item):
        if item.location:
            shapely_geom = to_shape(item.the_geom)
            geojson_geom = shapely.geometry.mapping(shapely_geom)
            geometry = geojson_geom
        else:
            geometry = None

        navigation = url_join(self.relative_url, item.featureid, "navigation")

        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "identifier": item.featureid,
                "source": "comid",
                "name": item.name,
                "comid": item.comid,
                "uri": item.uri,
                "reachcode": item.reachcode,
                "measure": item.measure,
                "navigation": navigation,
            },
        }
