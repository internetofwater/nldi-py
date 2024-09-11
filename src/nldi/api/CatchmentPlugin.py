from contextlib import contextmanager
from typing import Any, Dict, List, Union


from geoalchemy2 import WKTElement
import sqlalchemy
from sqlalchemy.engine import URL as DB_URL

from .. import LOGGER, util, NAD83_SRID
from ..schemas.nhdplus import CatchmentModel
from .BasePlugin import APIPlugin


class CatchmentPlugin(APIPlugin):
    def __init__(self, name):
        super().__init__(name)
        self.table_model = CatchmentModel
        self.geom_field = CatchmentModel.the_geom
        self.id_field = CatchmentModel.featureid

    @property
    def relative_url(self):
        return util.url_join(self.base_url, "linked-data", "comid")

    def get_by_id(self, id: str) -> Dict[str, Any]:
        LOGGER.debug(f"GET Catchment for: {id}")
        with self.session() as session:
            # Retrieve data from database as feature
            q = self.query(session)
            item = q.filter(self.id_field == id).first()
            if item is None:
                raise KeyError(f"No such source: featureid={id}.")
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
        LOGGER.debug(f"Fetching Catchment COMID by coordinates: {coords=}")
        with self.session() as session:
            geom = sqlalchemy.func.ST_AsGeoJSON(CatchmentModel.the_geom).label("geojson")
            # Retrieve data from database as feature
            point = WKTElement(coords, srid=NAD83_SRID)
            LOGGER.debug(f"Using this point for selection: {point}")
            intersects = sqlalchemy.func.ST_Intersects(CatchmentModel.the_geom, point)
            r = session.query(CatchmentModel).where(intersects).first()
            if r is None:
                raise KeyError
        LOGGER.info(f"Searching for Catchment under {coords}: Intersection with comid={r.featureid}")
        if as_feature:
            return self._sqlalchemy_to_feature(r)
        else:
            return r.featureid

    def _sqlalchemy_to_feature(self, item):
        navigation = url_join(self.relative_url, item.featureid, "navigation")

        return {
            "type": "Feature",
            "geometry": item.geojson,
            ##NOTE: this depends on the initial query returning ST_AsGeoJSON(the_geom) as geom.  See
            ##      the query() method inherited from BasePlugin.
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
