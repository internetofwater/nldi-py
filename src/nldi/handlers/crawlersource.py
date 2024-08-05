#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import sqlalchemy
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from .. import LOGGER
from ..schemas.nldi_data import CrawlerSourceModel
from . import BaseHandler
from .errors import ProviderItemNotFoundError, ProviderQueryError


class CrawlerSourceHandler(BaseHandler):
    def __init__(self, db_info):
        super().__init__(db_info)
        self.table_model = CrawlerSourceModel

    def get(self, identifier: str):
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

    def query(self, **kwargs):
        LOGGER.debug("Fetching sources")
        with self.session() as session:
            return [self._sqlalchemy_to_feature(item) for item in session.all()]

    # def align_sources(self, sources: list[dict]) -> bool:
    #     with Session(self._engine) as session:
    #         try:
    #             session.query(CrawlerSourceModel).delete()
    #             session.commit()
    #             [self._align_source(session, source) for source in sources]
    #         except ProgrammingError as err:
    #             LOGGER.warning(err)
    #             raise ProviderQueryError(err)

    #     return True

    # def _align_source(self, session, source):
    #     source_suffix = source["source_suffix"].lower()
    #     source["source_suffix"] = source_suffix
    #     LOGGER.debug(f"Creating source {source_suffix}")  # noqa
    #     session.add(CrawlerSourceModel(**source))
    #     session.commit()

    def _sqlalchemy_to_feature(self, item):
        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        feature = item_dict

        return feature
