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
from sqlalchemy import func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from nldi.lookup.base import (BaseLookup, ProviderQueryError,
                              ProviderItemNotFoundError)
from nldi.schemas.nldi_data import CrawlerSourceModel

LOGGER = logging.getLogger(__name__)


class CrawlerSourceLookup(BaseLookup):
    def __init__(self, provider_def):
        """
        CrawlerSourceLookup Class constructor

        :param provider_def: provider definitions from yml nldi-config.
                             data,id_field, name set in parent class
                             data contains the connection information
                             for class DatabaseCursor

        :returns: nldi.lookup.source.CrawlerSourceLookup
        """
        LOGGER.debug('Initialising Crawler Source.')
        super().__init__(provider_def)
        self.table_model = CrawlerSourceModel

    def get(self, identifier: str):
        source_name = identifier.lower()
        LOGGER.debug(f'Fetching source information for: {source_name}')

        with self.session() as session:
            # Retrieve data from database as feature
            source_suffix = func.lower(CrawlerSourceModel.source_suffix)
            item = (session
                    .filter(source_suffix == source_name)
                    .first())

            if item is None:
                msg = f'No such source: {self.id_field}={source_name}.'
                raise ProviderItemNotFoundError(msg)

            source = self._sqlalchemy_to_feature(item)
        return source

    def query(self):
        LOGGER.debug('Fetching sources')
        with self.session() as session:
            return [self._sqlalchemy_to_feature(item)
                    for item in session.all()]

    def align_sources(self, sources: list[dict]) -> bool:
        with Session(self._engine) as session:
            try:
                session.query(CrawlerSourceModel).delete()
                session.commit()
                [self._align_source(session, source) for source in sources]
            except ProgrammingError as err:
                LOGGER.warning(err)
                raise ProviderQueryError(err)

        return True

    def _align_source(self, session, source):
        source_suffix = source['source_suffix'].lower()
        source['source_suffix'] = source_suffix
        LOGGER.debug(f'Creating source {source_suffix}')  # noqa
        session.add(CrawlerSourceModel(**source))
        session.commit()

    def _sqlalchemy_to_feature(self, item):

        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop('_sa_instance_state')  # Internal SQLAlchemy metadata
        feature = item_dict

        return feature
