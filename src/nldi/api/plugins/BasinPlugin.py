#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# See the full copyright notice in LICENSE.md


import json
from typing import Any, Dict, List, Tuple, Union

import sqlalchemy
from geoalchemy2 import WKTElement

from ... import LOGGER, querybuilder, util
from ...schemas.nhdplus import CatchmentModel
from .APIPlugin import APIPlugin
from .CrawlerSourcePlugin import CrawlerSourcePlugin
from .FeaturePlugin import FeaturePlugin
from .FlowlinePlugin import FlowlinePlugin
from .HydroLocationPlugin import HydroLocationPlugin
from .SplitCatchmentPlugin import SplitCatchmentPlugin


class BasinPlugin(APIPlugin):
    SPLIT_CATCHMENT_THRESHOLD = 200

    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        super().__init__(name, **kwargs)
        self.table_model = CatchmentModel
        self.geom_field = CatchmentModel.the_geom
        self.id_field = CatchmentModel.featureid

    @property
    def crawler_source_lookup(self) -> CrawlerSourcePlugin:
        if self.is_registered:
            return self.parent.sources
        else:
            LOGGER.info("Attempt to get crawler_source_lookup from an unregistered plugin.")
            return CrawlerSourcePlugin("CrawlerSource-From-Basin", db_connect_url=self._db_connect_url)

    @property
    def feature_lookup(self) -> FeaturePlugin:
        if self.is_registered:
            self.parent.require_plugin("FeaturePlugin")
            return self.parent.plugins["FeaturePlugin"]
        else:
            LOGGER.info("Attempt to get feature_lookup from an unregistered plugin.")
            return FeaturePlugin("Feature-From-Basin", db_connect_url=self._db_connect_url)

    @property
    def flowline_lookup(self) -> FlowlinePlugin:
        if self.is_registered:
            self.parent.require_plugin("FlowlinePlugin")
            return self.parent.plugins["FlowlinePlugin"]
        else:
            LOGGER.info("Attempt to get flowline_lookup from an unregistered plugin.")
            return FlowlinePlugin("Flowline-From-Basin", db_connect_url=self._db_connect_url)

    @property
    def hydrolocation_lookup(self) -> HydroLocationPlugin:
        if self.is_registered:
            self.parent.require_plugin("HydroLocationPlugin")
            return self.parent.plugins["HydroLocationPlugin"]
        else:
            LOGGER.info("Attempt to get hydrolocation_lookup from an unregistered plugin.")
            return HydroLocationPlugin("HydroLocation-From-Basin", db_connect_url=self._db_connect_url)

    @property
    def splitcatchment_lookup(self) -> SplitCatchmentPlugin:
        if self.is_registered:
            self.parent.require_plugin("SplitCatchmentPlugin")
            return self.parent.plugins["SplitCatchmentPlugin"]
        else:
            LOGGER.info("Attempt to get splitcatchment_lookup from an unregistered plugin.")
            return SplitCatchmentPlugin("SplitCatchment-From-Basin", db_connect_url=self._db_connect_url)

    def get_by_id(
        self,
        identifier: str,
        source_name: str | None = None,
        simplified: bool = True,
        split: bool = False,
    ) -> List[Dict[str, Any]]:
        source_name = source_name.lower() if source_name else "comid"
        ## if unspecified, source_name is assumed to be comid

        (start_comid, is_point) = self._get_start_comid(identifier, source_name)

        if is_point and split:
            LOGGER.debug(f"Splitting Catchment:  {is_point=}, {split=}, {start_comid=}")
            point = self._get_point_on_flowline(identifier, source_name)

            if point is None:
                ## Plan B:
                LOGGER.debug("No point on flowline found.... trying find nearest point as backup.")
                distance = self._get_distance_from_flowine(identifier, source_name)
                LOGGER.debug(f"Computed Distance {distance}  (threshold={self.SPLIT_CATCHMENT_THRESHOLD})")

                if distance <= self.SPLIT_CATCHMENT_THRESHOLD:
                    point = self.func.get_closest(identifier, source_name)

                else:
                    ## Plan C:
                    [lon, lat] = feature["geometry"]["coordinates"]
                    wkt_geom = f"POINT({lon} {lat})"
                    response = self.hydrolocation_lookup(wkt_geom)
                    point = response["features"][0]["geometry"]["coordinates"]

            if point is None:  ## still no point
                msg = "Unable to retrieve point on flowline for catchment splitting."  # noqa
                raise ValueError(msg)

            [lon, lat] = point
            wkt_geom = f"POINT({lon} {lat})"
            features = [self.splitcatchment_lookup(wkt_geom)]
        else:
            features = [self._get_basin_from_comid(start_comid, simplified)]
        return features

    def _get_start_comid(self, identifier: str, source_name: str) -> Tuple[int, bool]:
        try:
            if source_name == "comid":
                self.flowline_lookup.get_by_id(identifier)
                start_comid = int(identifier)
                is_point = False
            else:
                #src = self.crawler_source_lookup.get_by_id(source_name)
                feature = self.feature_lookup.get_by_id(identifier, source_name)
                start_comid = int(feature["properties"]["comid"])
                is_point = feature["geometry"]["type"] == "Point"
        except KeyError:
            msg = f"The feature {identifier} does not exist for '{source_name}'."  # noqa
            raise KeyError(msg)
        return (start_comid, is_point)

    def _get_point_on_flowline(self, feature_id: str, feature_source: str):
        LOGGER.debug("Searching for point on flowline...")
        point_query = querybuilder.lookup_query.point_on_flowline(feature_id, feature_source)
        LOGGER.debug(point_query.compile(self._db_engine))

        try:
            with self.session() as session:
                result = session.execute(point_query).fetchone()
                if result is None or None in result:
                    LOGGER.warning("Not on flowline")
                    return None
                else:
                    return result
        except sqlalchemy.exc.SQLAlchemyError as e:
            LOGGER.error(f"Error retrieving point on flowline: {e}")
            return None

    def _get_distance_from_flowine(self, feature_id: str, feature_source: str):
        """
        Perform flowline distance

        :param feature_id: Feature indentifier
        :param feature_source: Feature source

        :returns: Distance from nearest flowline
        """
        point = querybuilder.lookup_query.distance_from_flowline(feature_id, feature_source)
        LOGGER.debug(point.compile(self._db_engine))

        with self.session() as session:
            result = session.execute(point).scalar()

            if result is None:
                LOGGER.warning("Not on flowline")
                return None
            else:
                return result

    def _get_closest_pt_on_flowline(self, feature_id: str, feature_source: str):
        point = querybuilder.lookup_query.get_closest_point_on_flowline(feature_id, feature_source)
        LOGGER.debug(point.compile(self._db_engine))

        with Session(self._engine) as session:
            # Retrieve data from database as feature
            result = session.execute(point).fetchone()

            if None in result:
                LOGGER.warning("Not on flowline")
            else:
                return result

    def _get_basin_from_comid(self, comid: int, simplified: bool):
        basin = querybuilder.basin_from_comid(comid, simplified)
        LOGGER.debug(basin.compile(self._db_engine))

        with self.session() as session:
            result = session.execute(basin).fetchone()
            if result is None:
                raise KeyError(f"No such item: {self.id_field}={comid}")

            return {
                "type": "Feature",
                "geometry": json.loads(result.the_geom),
                "properties": {},
            }
