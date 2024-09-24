#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
#

""" Mainstem Plugin. """

from typing import Any, Dict

from ... import LOGGER
from ...schemas.nldi_data import MainstemLookupModel
from .APIPlugin import APIPlugin


class MainstemPlugin(APIPlugin):
    """
    Provides a mechanism to query the NHDPlus data for mainstem features.

    A mainstem is a single flowline that represents the main channel of a river. This plugin
    allows a mainstem to be retrieved by its NHDPlus COMID. Unlike many other plugins, this
    lookup does not produce a GeoJSON feature, but rather a dictionary of properties related to
    the mainstem. Mainstem lookups to not include geometry data.
    """

    def __init__(self, name: str | None = None, **kwargs: Dict[str, Any]):
        super().__init__(name, **kwargs)
        self.id_field = MainstemLookupModel.nhdpv2_comid
        self.table_model = MainstemLookupModel

    def get_by_id(self, identifier: str) -> Dict[str, Any]:
        """
        Retrieve a mainstem by its NHDPlus COMID.

        :param identifier: COMID of the mainstem to retrieve
        :type identifier: str
        :raises KeyError: If the COMID is not found
        :return: Dictionary of properties representing the mainstem
        :rtype: Dict[str, Any]
        """
        LOGGER.debug(f"{self.__class__.__name__} GET mainstem for: {identifier}")
        with self.session() as session:
            # Retrieve data from database as feature
            item = session.query(self.table_model).where(self.id_field == identifier).first()
            if not item:
                raise KeyError("No Mainstem found {self.id_field}={identifier}")
            mainstem = self._sqlalchemy_to_feature(item)
        return mainstem

    def _sqlalchemy_to_feature(self, item: MainstemLookupModel) -> Dict[str, Any]:
        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        return item_dict
