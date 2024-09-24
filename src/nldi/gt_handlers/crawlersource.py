#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

from typing import Dict, List

import sqlalchemy
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from .. import LOGGER
from ..schemas.nldi_data import CrawlerSourceModel
from . import BaseHandler
from .errors import ProviderItemNotFoundError, ProviderQueryError


class CrawlerSourceHandler(BaseHandler):
    """
    Implements a handler for the CrawlerSourceModel table.

    Unlike other handlers, this handler can update the sources in the database,
    so needs to have write credentials.
    """

    def __init__(self, db_info):
        super().__init__(db_info)
        self.table_model = CrawlerSourceModel

    def get(self, identifier: str):
        """Retrieve a source from the database."""
        source_name = identifier.lower()
        LOGGER.debug(f"Fetching source information for: {source_name}")

        with self.session() as session:
            # Retrieve data from database as feature
            source_suffix = sqlalchemy.func.lower(CrawlerSourceModel.source_suffix)
            item = session.filter(source_suffix == source_name).first()

            if item is None:
                msg = f"No such source: {self.id_field}={source_name}."
                raise ProviderItemNotFoundError(msg)

            source = self._sqlalchemy_to_feature(item)
        return source

    def query(self) -> List[Dict]:
        """List all items in the self.table_model table."""
        LOGGER.debug("Fetching all sources from %s", self.table_model.__tablename__)
        with self.session() as session:
            return [self._sqlalchemy_to_feature(item) for item in session.all()]

    def align_sources(self, sources: List[Dict[str, str]]) -> bool:
        """
        Align the sources in the database with the provided list of sources.

        This will delete all sources in the database and replace them with the sources
        in the provided list. The list is assumed to be well-formatted with valid
        sources and all keys/columns present.
        """
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
        source_suffix = source["source_suffix"].lower()
        source["source_suffix"] = source_suffix
        LOGGER.debug(f"Creating source {source_suffix}")  # noqa
        session.add(CrawlerSourceModel(**source))
        session.commit()

    def _sqlalchemy_to_feature(self, item):
        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        feature = item_dict

        return feature
