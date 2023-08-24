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
import logging
import shapely
from typing import Iterable

from nldi.lookup.base import BaseLookup, ProviderItemNotFoundError
from nldi.schemas.nhdplus import FlowlineModel
from nldi.util import url_join

LOGGER = logging.getLogger(__name__)


class FlowlineLookup(BaseLookup):

    def __init__(self, provider_def):
        """
        FlowlineLookup Class constructor

        :param provider_def: provider definitions from yml nldi-config.
                             data, id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor

        :returns: nldi.lookup.flowline.FlowlineLookup
        """
        LOGGER.debug('Initialising Flowline Lookup')
        self.base_url = provider_def['base_url']
        self.relative_url = url_join(self.base_url, 'linked-data/comid')

        super().__init__(provider_def)
        self.id_field = 'featureid'
        self.table_model = FlowlineModel

    def get(self, identifier: str):
        LOGGER.debug(f'Fetching comid with id: {identifier}')
        with self.session() as session:
            # Retrieve data from database as feature
            item = session.get(identifier)

            if item is None:
                msg = f'No comid found for: {identifier}.'
                raise ProviderItemNotFoundError(msg)

            LOGGER.debug(f'Intersection with {item.nhdplus_comid}')
            fc = {
                'type': 'FeatureCollection',
                'features': [self._sqlalchemy_to_feature(item)]
            }

        return fc

    def lookup_navigation(self, comids: Iterable[str]):
        with self.session() as session:
            # Retrieve data from database as feature
            query = (session
                     .filter(FlowlineModel.nhdplus_comid.in_(comids)))
            hits = query.count()

            if hits is None:
                msg = 'Not found'
                raise ProviderItemNotFoundError(msg)

            LOGGER.debug(f'Returning {hits} hits')
            fc = {
                'type': 'FeatureCollection',
                'features': [self._sqlalchemy_to_feature(item)
                             for item in query.all()]
            }

        return fc

    def _sqlalchemy_to_feature(self, item):
        if item.shape:
            shapely_geom = to_shape(item.shape)
            geojson_geom = shapely.geometry.mapping(shapely_geom)
            geometry = geojson_geom
        else:
            geometry = None

        try:
            mainstem = item.mainstem_lookup.uri
        except AttributeError:
            mainstem = ''

        navigation = url_join(self.relative_url,
                              item.nhdplus_comid, 'navigation')

        return {
            'type': 'Feature',
            'properties': {
                'identifier': item.permanent_identifier,
                'source': 'comid',
                'sourceName': 'NHDPlus comid',
                'comid': item.nhdplus_comid,
                'mainstem': mainstem,
                'navigation': navigation
            },
            'geometry': geometry
        }
