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

import json
from typing import Iterable


from nldi.lookup.base import BaseLookup, ProviderItemNotFoundError
from nldi.schemas.nldi_data import FeatureSourceModel
from nldi.util import url_join

from .. import LOGGER


class FeatureLookup(BaseLookup):
    def __init__(self, provider_def):
        """
        FeatureLookup Class constructor

        :param provider_def: provider definitions from yml nldi-config.
                             data,id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor

        :returns: nldi.lookup.feature.FeatureLookup
        """
        LOGGER.debug("Initialising Feature Source.")
        self.source = provider_def["source"]
        self.source_name = self.source["source_suffix"]
        self.base_url = provider_def["base_url"]
        self.relative_url = url_join(self.base_url, "linked-data", self.source_name)

        super().__init__(provider_def)
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
