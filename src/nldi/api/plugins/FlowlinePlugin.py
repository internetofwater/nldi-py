#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# See the full copyright notice in LICENSE.md

"""Flowline Plugin"""

import json
from functools import cached_property
from typing import Any, Dict

import sqlalchemy

from ... import LOGGER, util
from ...schemas.nhdplus import FlowlineModel
from .APIPlugin import APIPlugin


class FlowlinePlugin(APIPlugin):
    """
    NHD Flowline Plugin

    This plugin provides a mechanism to query the NHDPlus flowline data.
    ``NHDFlowine`` is a table in the NHDPlus database holding information about the surface
    drainage network. See https://www.usgs.gov/ngp-standards-and-specifications/national-hydrography-dataset-nhd-data-dictionary-feature-classes

    This plugin allows a flowline to be retrieved by its NHDPlus COMID. The returned
    data is a GeoJSON ``Feature`` representing the flowline geometry and minimal properties
    related to navigation up and down stream.
    """

    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        super().__init__(name, **kwargs)
        self.geom_field = FlowlineModel.shape
        self.id_field = FlowlineModel.nhdplus_comid
        self.table_model = FlowlineModel

    @property
    def relative_url(self):
        """
        Get the relative URL used to construct properties of the returned GeoJSON.

        Some properties of the returned feature are URLs which indicate subsequent services
        that can be used to retrieve additional information about the feature (e.g. navigation).
        This property is used as the base of those URLs, as they are all relative to this
        plugin's base URL.

        The relative url is dependent on the parent's (i.e. the ``API``) base URL.  For un-registered
        plugins, a default URL is returned.

        :return: The relative URL for this plugin
        :rtype: str
        """
        if self.is_registered:
            return util.url_join(self.parent.base_url, "linked-data/comid")
        else:
            LOGGER.info("Attempt to get relative_url from an unregistered plugin.")
            return "/linked-data/comid"

    def get_by_id(self, identifier: str) -> Dict[str, Any]:
        """
        Retrieve a flowline by its NHDPlus COMID.

        :param identifier: COMID of the flowline to retrieve
        :type identifier: str
        :raises KeyError: If the COMID is not found
        :return: GeoJSON feature representing the flowline
        :rtype: Dict[str, Any]
        """
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

    def lookup_navigation(self, nav: str):
        """
        TODO:  Fuller description of navigation lookup

        :param nav: _description_
        :type nav: str
        :raises KeyError: _description_
        :return: _description_
        :rtype: _type_
        """
        with self.session() as session:
            geojson = sqlalchemy.func.ST_AsGeoJSON(self.geom_field).label("geojson")
            q = session.query(self.table_model, geojson).join(nav, FlowlineModel.nhdplus_comid == nav.c.comid)
            _hits = q.count()
            if q.count() is None:
                raise KeyError(f"No features found for {source_suffix=}.")
            LOGGER.debug(f"Query returned {_hits} hits.")
            _results = []
            for item in q.all():
                _results.append(self._sqlalchemy_to_feature(item))
        return _results

    def trim_navigation(self, nav, nav_trim):
        """
        TODO: Fuller description of trimmed navigation.

        :param nav: _description_
        :type nav: _type_
        :param nav_trim: _description_
        :type nav_trim: _type_
        :return: _description_
        :rtype: _type_
        """
        with self.session() as session:
            q = (
                session.query(self.table_model, nav_trim.c.geojson)
                .join(nav, FlowlineModel.nhdplus_comid == nav.c.comid)
                .join(nav_trim, FlowlineModel.nhdplus_comid == nav_trim.c.comid)
            )
            _hits = q.count()
            if _hits is None:
                KeyError("Not Found")
            LOGGER.debug(f"Trim Navigation query returned {_hits} hits.")
            _results = []
            for item in q.all():
                _results.append(self._sqlalchemy_to_feature(item))
            return _results

    def _sqlalchemy_to_feature(self, item) -> Dict[str, Any]:
        """
        Turn a SQLAlchemy result into a GeoJSON feature.

        :param item: A tuple of (FlowlineModel, geojson)
        :type item: Tuple[FlowlineModel, str]
        :return: A GeoJSON feature
        :rtype: Dict[str, Any]
        """
        (feature, geojson) = item

        try:
            mainstem = item.mainstem_lookup.uri
        except AttributeError:
            LOGGER.info(f"Mainstem not found for {feature.nhdplus_comid}")
            mainstem = ""

        navigation = util.url_join(self.relative_url, feature.nhdplus_comid, "navigation")

        return {
            "type": "Feature",
            "properties": {
                "identifier": str(feature.permanent_identifier),
                "source": "comid",
                "sourceName": "NHDPlus comid",
                "comid": str(feature.nhdplus_comid),
                # "mainstem": mainstem,  ##< mainstem is not in current production reponse from labs.waterdata.usgs.gov
                "navigation": navigation,
            },
            "geometry": json.loads(geojson),
        }
