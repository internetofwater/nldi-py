#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import json
from typing import Any, Dict, List, Union

import sqlalchemy
from geoalchemy2 import WKTElement

from ... import LOGGER, NAD83_SRID, util
from ..schemas.nhdplus import CatchmentModel
from . import APIPlugin, CrawlerSourcePlugin, FlowlinePlugin, FeaturePlugin


class BasinPlugin(APIPlugin):
    def __init__(self, name, **kwargs):
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

    def get_by_id(
        self,
        identifier: str,
        source_name: str | None = None,
        simplify: bool = True,
        split: bool = False,
    ) -> Tuple[dict, int, str]:
        source_name = source_name.lower() if source_name else "comid"
        ## if unspecified, source_name is assumed to be comid

        try:
            if source_name != "comid":
                src = self.crawler_source_lookup(source_name)
                feature = self.feature_lookup.get_by_id(identifier, source_name)
                start_comid = int(feature["properties"]["comid"])
                is_point = feature["geometry"]["type"] == "Point"
            else:
                self.flowline_lookup.get_by_id(identifier)
                start_comid = int(identifier)
                isPoint = False
        except KeyError:
            msg = f"The feature {identifier} does not exist for '{source_name}'."  # noqa
            raise KeyError(msg)

        if isPoint and split:
            LOGGER.debug("Performing Split Catchment")
            ## TODO: wtf is this?
            point = self.func.get_point(identifier, source_name)

            if point is None:
                distance = self.func.get_distance(identifier, source_name)
                LOGGER.debug(f"Distance distance)

                if distance <= SPLIT_CATCHMENT_THRESHOLD:
                    point = self.func.get_closest(identifier, source_name)
                else:
                    [lon, lat] = feature["geometry"]["coordinates"]
                    wkt_geom = f"POINT({lon} {lat})"
                    response = self.pygeoapi_lookup.get_hydrolocation(wkt_geom)
                    point = response["features"][0]["geometry"]["coordinates"]

            if point is None:
                msg = "Unable to retrieve point on flowline for catchment splitting."  # noqa
                return self.get_exception(
                    HTTPStatus.INTERNAL_SERVER_ERROR, headers, request.format, "NoApplicableCode", msg
                )

            [lon, lat] = point
            wkt_geom = f"POINT({lon} {lat})"
            features = self.pygeoapi_lookup.get_split_catchment(wkt_geom)
        else:
            LOGGER.debug(f"Returning with simplified geometry: {simplified}")
            features = self.func.get_basin(start_comid, simplified)

        content = stream_j2_template("FeatureCollection.j2", features)
        return headers, HTTPStatus.OK, content
