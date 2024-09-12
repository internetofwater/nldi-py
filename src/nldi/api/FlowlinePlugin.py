#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import json
import logging
from functools import cached_property
from typing import Dict, Any

import sqlalchemy
from .. import LOGGER, util
from ..schemas.nhdplus import FlowlineModel
from .BasePlugin import APIPlugin


class FlowlinePlugin(APIPlugin):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.geom_field = FlowlineModel.shape
        self.id_field = FlowlineModel.nhdplus_comid
        self.table_model = FlowlineModel

    @property
    def relative_url(self):
        if self.is_registered:
            return util.url_join(self.parent.base_url, "linked-data/comid")
        else:
            LOGGER.warning("Attempt to get relative_url from an unregistered plugin.")
            return "/linked-data/comid"

    def get(self, identifier: str) -> Dict[str, Any]:
        LOGGER.debug(f"{self.__class__.__name__} : Fetching COMID with {identifier=}")
        with self.session() as session:
            # Retrieve data from database as feature
            try:
                q = self.query(session)
                item = q.filter(self.id_field == identifier).first()
            except sqlalchemy.exc.SQLAlchemyError as e:
                LOGGER.error(f"SQLAlchemy error: {e}")
                # Doesn't really matter what the error is, the end result is that we couldn't find the named key.  Raise KeyError
                raise KeyError from e

            if item is None:
                LOGGER.debug(f"Not found: {identifier=}")
                raise KeyError("No comid found for: {identifier=}")
            # NOTE: item is a tuple of (FlowlineModel, geom)
            return self._sqlalchemy_to_feature(item)

    def lookup_navigation(self, nav: str):  ## TODO: navigation business logic refactor
        with self.session() as session:
            q = self.query(session)  # Retrieve data from database as feature
            query = q.join(nav, FlowlineModel.nhdplus_comid == nav.c.comid)
            hits = query.count()

            if hits is None:
                raise KeyError("Not Found")
            LOGGER.debug(f"Found {hits} hits")
            for item in query.all():
                yield self._sqlalchemy_to_feature(item)

    def trim_navigation(self, nav, nav_trim):  ## TODO: navigation business logic refactor
        with self.session() as session:
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

    def _sqlalchemy_to_feature(self, item) -> Dict[str, Any]:
        if self.geom_field:
            (feature, geojson) = item
            geometry = json.loads(geojson)
        else:
            feature = item
            geometry = None

        try:
            mainstem = item.mainstem_lookup.uri
        except AttributeError:
            mainstem = ""

        navigation = util.url_join(self.relative_url, feature.nhdplus_comid, "navigation")

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
