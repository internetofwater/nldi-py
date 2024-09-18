#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import json
from typing import Any, Dict, List, Union

import sqlalchemy
from geoalchemy2 import WKTElement

from ... import LOGGER, NAD83_SRID, util
from ...schemas.nldi_data import FeatureSourceModel

from .APIPlugin import APIPlugin
from .CrawlerSourcePlugin import CrawlerSourcePlugin


class FeaturePlugin(APIPlugin):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.geom_field = FeatureSourceModel.location
        self.id_field = FeatureSourceModel.identifier
        self.table_model = FeatureSourceModel
        self.table_model.__tablename__ = "feature"

    def relative_url(self, srcname: str) -> str:
        if self.is_registered:
            return util.url_join(self.parent.base_url, "linked-data/{srcname}")
        else:
            LOGGER.warning("Attempt to get relative_url from an unregistered plugin.")
            return "/linked-data/{srcname}"

    @property
    def crawler_source_lookup(self) -> CrawlerSourcePlugin:
        if self.is_registered:
            return self.parent.sources
        else:
            LOGGER.warning("Attempt to get crawler_source_lookup from an unregistered plugin.")
            return CrawlerSourcePlugin("CrawlerSource-From-Feature", db_connect_url=self._db_connect_url)

    def get_by_id(self, id: str, source_suffix: str) -> Dict[str, Any]:
        """Retrieve a feature by its unique id and source."""
        LOGGER.info(f"{self.__class__.__name__} GET Feature by ID: {id=} from {source_suffix=}")

        LOGGER.debug(f"Getting source information for {source_suffix=}")
        try:
            src = self.crawler_source_lookup.get(source_suffix)
        except KeyError:
            raise KeyError(f"Source not found: {source_suffix=}")

        with self.session() as session:
            geojson = sqlalchemy.func.ST_AsGeoJSON(self.geom_field).label("geojson")
            q = session.query(self.table_model, geojson)
            item = q.where(self.id_field == id).filter(self.table_model.crawler_source_id == src['crawler_source_id']).first()
            if item is None:
                raise KeyError(f"No such feature found: {id=} / {source_suffix=}.")
            row, geojson = item
            ## NOTE: We have to call this here (while session is active) so that the database relationships can be resolved.
            result =  self._sqlalchemy_to_feature(row, geojson, src)
        return result

    def get_all(self, source_suffix: str) -> List[Dict[str, Any]]:
        LOGGER.info(f"{self.__class__.__name__} GET all features from {source_suffix=}")
        LOGGER.debug(f"Getting source information for {source_suffix=}")
        try:
            src = self.crawler_source_lookup.get(source_suffix)
        except KeyError:
            raise KeyError(f"Source not found: {source_suffix=}")

        with self.session() as session:
            # Retrieve data from database as feature
            geojson = sqlalchemy.func.ST_AsGeoJSON(self.geom_field).label("geojson")
            q = session.query(self.table_model, geojson).filter(self.table_model.crawler_source_id == src['crawler_source_id']).order_by(self.table_model.identifier)

            _hits = q.count()
            if q.count() is None:
                raise KeyError(f"No features found for {source_suffix=}.")
            LOGGER.debug(f"Query returned {_hits} hits.")

            _return = []  ##TODO: This should really be a generator, but the db connection keeps closing after only a handful of rows processed.

            for item in q:
                row, geojson = item
                _return.append(self._sqlalchemy_to_feature(row, geojson, src))
        return _return

    def lookup_navigation(self, nav: str):
        raise NotImplementedError("FeaturePlugin.lookup_navigation() is not implemented.")
        # crawler_source_id = self.source.get("crawler_source_id")
        # crawler_source_id_ = FeatureSourceModel.crawler_source_id

        # with self.session() as session:
        #     # Retrieve data from database as feature
        #     query = session.join(nav, self.table_model.comid == nav.c.comid).filter(
        #         crawler_source_id_ == crawler_source_id
        #     )
        #     hits = query.count()

        #     if hits is None:
        #         raise ProviderItemNotFoundError("Not found")

        #     LOGGER.debug(f"Returning {hits} hits")
        #     for item in query.all():
        #         yield self._sqlalchemy_to_feature(item)

    def _sqlalchemy_to_feature(self, feature, geojson, srcinfo) -> Dict[str, Any]:
        try:
            mainstem = feature.mainstem_lookup.uri
        except AttributeError:
            LOGGER.warning(f"Mainstem_lookup not found for {feature.identifier}")
            mainstem = ""
        navigation = util.url_join(self.relative_url( srcinfo['source_suffix'] ), feature.identifier, "navigation")

        return {
            "type": "Feature",
            "properties": {
                "identifier": feature.identifier,
                "name": feature.name,
                "source": srcinfo['source_suffix'],
                "sourceName": srcinfo['source_name'],
                "comid": feature.comid,
                "type": srcinfo['feature_type'],
                "uri": feature.uri,
                "reachcode": feature.reachcode,
                "measure": feature.measure,
                "navigation": navigation,
                "mainstem": mainstem,
            },
            "geometry": json.loads(geojson),
        }

