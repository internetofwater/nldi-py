#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import json
import logging
from typing import Iterable

from .. import LOGGER
from ..schemas.nhdplus import FlowlineModel
from ..util import url_join
from . import BaseHandler
from .errors import ProviderItemNotFoundError


class FlowlineHandler(BaseHandler):
    def __init__(self, provider_def):
        super().__init__(provider_def)
        self.base_url = provider_def["base_url"]
        self.relative_url = url_join(self.base_url, "linked-data/comid")
        self.geom_field = FlowlineModel.shape
        self.id_field = FlowlineModel.nhdplus_comid
        self.table_model = FlowlineModel

    def get(self, identifier: str):
        LOGGER.debug(f"{self.__class__.__name__} : Fetching COMID with {identifier=}")
        with self.session() as session:
            # Retrieve data from database as feature
            item = session.filter(self.id_field == identifier).first()

            if item is None:
                msg = f"No comid found for: {identifier=}."
                raise ProviderItemNotFoundError(msg)

            # NOTE: item is a tuple of (FlowlineModel, geom)
            LOGGER.debug(f"> Intersection with {item[0].nhdplus_comid}")
            return self._sqlalchemy_to_feature(item)

    def lookup_navigation(self, nav: str):
        with self.session() as session:
            # Retrieve data from database as feature
            query = session.join(nav, FlowlineModel.nhdplus_comid == nav.c.comid)
            hits = query.count()

            if hits is None:
                msg = "Not found"
                raise ProviderItemNotFoundError(msg)

            LOGGER.debug(f"Returning {hits} hits")
            for item in query.all():
                yield self._sqlalchemy_to_feature(item)

    def trim_navigation(self, nav, nav_trim):
        with self.session(raw=True) as session:
            # Retrieve data from database as feature
            query = (
                session.query(self.table_model, nav_trim.c.geom)
                .join(nav, FlowlineModel.nhdplus_comid == nav.c.comid)
                .join(
                    nav_trim,
                    FlowlineModel.nhdplus_comid == nav_trim.c.comid,  # noqa
                )
            )
            hits = query.count()

            if hits is None:
                msg = "Not found"
                raise ProviderItemNotFoundError(msg)

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
            mainstem = item.mainstem_lookup.uri
        except AttributeError:
            mainstem = ""

        navigation = url_join(self.relative_url, feature.nhdplus_comid, "navigation")

        return {
            "type": "Feature",
            "properties": {
                "identifier": feature.permanent_identifier,
                "source": "comid",
                "sourceName": "NHDPlus comid",
                "comid": feature.nhdplus_comid,
                "mainstem": mainstem,
                "navigation": navigation,
            },
            "geometry": geometry,
        }
