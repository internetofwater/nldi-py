#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import json
from typing import Iterable

from .. import LOGGER
from ..schemas.nldi_data import FeatureSourceModel
from ..util import url_join
from . import BaseHandler
from .errors import ProviderItemNotFoundError, ProviderQueryError


class FeatureHandler(BaseHandler):
    """
    Lookup a feature by identifier or query features by source.

    Features are stored in multiple tables, one for each source. The "master" feature
    table is a view that unions all the source tables. This handler is used to query
    a particular source table to find a specific feature by its ID.
    """

    def __init__(self, provider_def):
        super().__init__(provider_def)

        self.source = provider_def["source"]
        self.source_name = self.source["source_suffix"]
        self.base_url = provider_def["base_url"]
        self.relative_url = url_join(self.base_url, "linked-data", self.source_name)

        self.geom_field = FeatureSourceModel.location
        self.id_field = FeatureSourceModel.identifier
        self.table_model = FeatureSourceModel
        self.table_model.__tablename__ = f"feature_{self.source_name}"

    def get(self, identifier: str):
        identifier = str(identifier)
        LOGGER.debug(f"Fetching {identifier}")

        with self.session() as session:
            # Retrieve data from database as feature
            item = session.filter(self.id_field == identifier).first()

            if item is None:
                msg = f"No such item: {self.id_field}={identifier}"
                raise ProviderItemNotFoundError(msg)

            return self._sqlalchemy_to_feature(item)

    def query(self):
        crawler_source_id = self.source.get("crawler_source_id")
        crawler_source_id_ = FeatureSourceModel.crawler_source_id

        LOGGER.debug(f"Fetching features for source id: {crawler_source_id}")
        with self.session() as session:
            # Retrieve data from database as feature
            query = session.filter(crawler_source_id_ == crawler_source_id)
            hits = query.count()

            if hits is None:
                msg = f"Not found {crawler_source_id_}={crawler_source_id}"
                raise ProviderItemNotFoundError(msg)

            LOGGER.debug(f"Returning {hits} hits")
            for item in query.all():
                yield self._sqlalchemy_to_feature(item)

    def lookup_navigation(self, nav: str):
        crawler_source_id = self.source.get("crawler_source_id")
        crawler_source_id_ = FeatureSourceModel.crawler_source_id

        with self.session() as session:
            # Retrieve data from database as feature
            query = session.join(nav, self.table_model.comid == nav.c.comid).filter(
                crawler_source_id_ == crawler_source_id
            )
            hits = query.count()

            if hits is None:
                raise ProviderItemNotFoundError("Not found")

            LOGGER.debug(f"Returning {hits} hits")
            for item in query.all():
                yield self._sqlalchemy_to_feature(item)

    def _sqlalchemy_to_feature(self, item):
        if self.geom_field:
            (feature, geom) = item
            geometry = json.loads(geom)
        else:
            feature = item
            geometry = None

        try:
            mainstem = feature.mainstem_lookup.uri
        except AttributeError:
            mainstem = ""

        navigation = url_join(self.relative_url, feature.identifier, "navigation")

        return {
            "type": "Feature",
            "properties": {
                "identifier": feature.identifier,
                "name": feature.name,
                "source": feature.crawler_source.source_suffix,
                "sourceName": feature.crawler_source.source_name,
                "comid": feature.comid,
                "type": feature.crawler_source.feature_type,
                "uri": feature.uri,
                "reachcode": feature.reachcode,
                "measure": feature.measure,
                "navigation": navigation,
                "mainstem": mainstem,
            },
            "geometry": geometry,
        }
