#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Mixin to allow exporting a model as GeoJSON."""

import logging
from typing import Any

import geoalchemy2
from geomet import wkb, wkt
from sqlalchemy import inspect
from sqlalchemy.ext.associationproxy import AssociationProxyExtensionType
from sqlalchemy.orm import declarative_mixin, declared_attr

from nldi.db.schemas import struct_geojson


@declarative_mixin
class GeoJSONMixin:
    """
    SQLAlchemy mixin to augment functionality of geo-enabled table models.

    This mixin lets you output an instantiated model as a GeoJSON-like
    data structure.  All columns except the geo column are treated as members
    of the ``properties`` dict.  The geo column is converted to GeoJSON
    via ``geoalchemy2``'s ``to_shape()`` utility function.
    """

    @declared_attr.directive
    @classmethod
    def __geo_column__(cls) -> str:
        """
        Attempt to guess the name of the column holding the spatial data.

        This is a simple-minded linear search of the columns by name.  It will stop at the
        first column with a declared type matching a geoalchemy2.Geography or
        geoalchemy2.Geometry data type. If none is found, an exception is raised.

        Unfortunately, conventional caching decorators can't be utilized here (on this
        ``classmethod``), so we will do need to do this search every time we need the
        name of the geo column on instances.

        You can override this search by manually setting ``__geo_column__`` as a member
        in the model itself, effectively nullifying this class method and going with
        that static value.
        """
        for col in cls.__table__.columns:
            if isinstance(col.type, geoalchemy2.Geometry) or isinstance(col.type, geoalchemy2.Geography):
                return col.name
        raise ValueError("No Geometry/Geography column found.")

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Create GeoJSON-like dict out of geospatial column data."""
        _geometry = getattr(self, self.__geo_column__)
        return geoalchemy2.shape.to_shape(_geometry).__geo_interface__
        ## TODO: This mechanism relies on ``shapely`` under the covers of to_shape().
        ## That's a big dependency for such a simple conversion.
        ## Can we use ``geomet`` or something else to turn a geoalchemy Element into GeoJSON?

    def __properties__(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """Mimic the ``properties`` member of a GeoJSON feature."""
        exclude = {self.__geo_column__}.union(exclude or [])  # geom data should not be a member of properties
        ## Explicitly include columns by name (if not in the exclude set)
        _props = {col.name: getattr(self, col.name) for col in self.__table__.columns if col.name not in exclude}
        ## NOTE: This explicitly loops through the defined columns; it does **not** include any
        ## association proxies (because they're not columns, really).  You'll want to add those yourself.
        return _props

    def as_feature(
        self,
        rename_fields: dict[str, str] | None = None,
        xtra_props: dict[str, str] | None = None,
        excl_props: set[str] | None = None,
    ) -> struct_geojson.Feature:
        """
        Returns a GeoJSON-like feature, with ``geometry`` and ``properties`` set.

        :param rename_fields: Dictionary holding field renaming information
        :type rename_fields: dict[str, str] | None, optional
        :param xtra_props: Additional keys/values to add to the properties dict
        :type xtra_props: dict[str,str] | None, optional
        :param excl_props: Model members to exclude from the properties dict
        :type excl_props: set[str] | None, optional
        :return: A GeoJSON representation of this model, structured according to
        :rtype: struct_geojson.Feature
        """
        # NOTE: We do a lot of work here related to renaming, adding, excluding properties.  This
        # is starting to get into DTO territory, rather than a simple dump of the model as a
        # GeoJSON-like object.

        # TODO: Revisit whether this functionality belongs in DTO or service layer.
        _pkcols = [col for col in inspect(self.__class__).columns if col.primary_key]
        _props = self.__properties__(exclude=excl_props)
        if rename_fields:
            for k, v in rename_fields.items():
                _props[v] = _props.pop(k)
        if xtra_props:
            _props.update(xtra_props)

        # NOTE: ``id`` is required to be a JSON string or an integer; I take that to be the
        # value of the first primary_key column.
        return struct_geojson.Feature(
            id=getattr(self, _pkcols[0].name),
            geometry=self.__geo_interface__,
            properties=_props,
        )
