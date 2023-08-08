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

import logging

from nldi.lookup.base import BaseLookup, ProviderItemNotFoundError
from nldi.schemas.nldi_data import MainstemLookupModel

LOGGER = logging.getLogger(__name__)


class MainstemLookup(BaseLookup):

    def __init__(self, provider_def):
        """
        MainstemLookup Class constructor

        :param provider_def: provider definitions from yml nldi-config.
                             data, id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor

        :returns: nldi.lookup.mainstem.MainstemLookup
        """
        LOGGER.debug('Initialising Mainstem Lookup.')
        super().__init__(provider_def)
        self.id_field = 'nhdpv2_comid'
        self.table_model = MainstemLookupModel

    def get(self, identifier: str):
        LOGGER.debug(f'Fetching mainstem for: {identifier}')
        with self.session() as session:
            # Retrieve data from database as feature
            item = session.get(identifier)
            if item is None:
                msg = f'No mainstem found: {self.id_field}={identifier}.'
                raise ProviderItemNotFoundError(msg)
            mainstem = self._sqlalchemy_to_feature(item)

        return mainstem

    def _sqlalchemy_to_feature(self, item):

        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop('_sa_instance_state')  # Internal SQLAlchemy metadata
        feature = item_dict

        return feature
