#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

from .. import LOGGER
from ..schemas.nldi_data import MainstemLookupModel
from . import BaseHandler
from .errors import ProviderItemNotFoundError


class MainstemHandler(BaseHandler):
    def __init__(self, provider_def):
        super().__init__(provider_def)
        self.id_field = MainstemLookupModel.nhdpv2_comid
        self.table_model = MainstemLookupModel

    def get(self, identifier: str):
        LOGGER.debug(f"{self.__class__.__name__} Fetching mainstem for: {identifier=}")
        with self.session() as session:
            # Retrieve data from database as feature
            item = session.filter(self.id_field == identifier).first()

            if item is None:
                raise ProviderItemNotFoundError(f"> No mainstem found: {self.id_field}={identifier}.")
            mainstem = self._sqlalchemy_to_feature(item)

        return mainstem

    def _sqlalchemy_to_feature(self, item):
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        return item_dict
