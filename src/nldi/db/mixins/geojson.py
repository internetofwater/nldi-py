#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Mixin to allow exporting a model as GeoJSON."""

from typing import Any

import geoalchemy2
from advanced_alchemy.exceptions import ImproperConfigurationError
from sqlalchemy.orm import declarative_mixin, declared_attr


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
        geoalchemy2.Geometry data type. If none is found, raises ``advanced_alchemy.exceptions.ImproperConfigurationError``.

        You can override this search by manually setting ``__geo_column__`` as a member
        in the table model itself, effectively nullifying this class method and going with
        that static value.
        """
        for col in cls.__table__.columns:
            if isinstance(col.type, geoalchemy2.Geometry) or isinstance(col.type, geoalchemy2.Geography):
                return col.name
        raise ImproperConfigurationError(f"No geometry or geography column found in {cls.__name__}")

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """
        Create GeoJSON-like dict out of geospatial column data.

        This mechanism relies on ``shapely`` under the covers of ``geoalchemy2.shape.to_shape()``.
        That's a big dependency for such a simple conversion.  A possible alternative would be to
        fetch the GeoJSON directly from the database using ``ST_AsGeoJSON`` -- but this requires
        that a session be active in order to make the query.
        """
        ## TODO: Can we use ``geomet`` or something else to turn a geoalchemy WKBElement into GeoJSON?
        _geometry = getattr(self, self.__geo_column__)
        return geoalchemy2.shape.to_shape(_geometry).__geo_interface__

    def __properties__(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """Mimic the ``properties`` member of a GeoJSON feature."""
        exclude = {self.__geo_column__}.union(exclude or [])  # geom data should not be a member of properties
        return {col.name: getattr(self, col.name) for col in self.__table__.columns if col.name not in exclude}

    def as_feature(
        self,
        rename_fields: dict[str, str] | None = None,
        xtra_props: dict[str, str] | None = None,
        excl_props: set[str] | None = None,
    ) -> dict[str, Any]:
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
        _primary_keys = [k.name for i in self.__class__.__mapper__.primary_key]

        _props = self.__properties__(exclude=excl_props)
        if rename_fields:
            for k, v in rename_fields.items():
                _props[v] = _props.pop(k)
        if xtra_props:
            _props.update(xtra_props)
        return dict(
            id=getattr(self, _primary_keys[0]),
            geometry=self.__geo_interface__,
            properties=_props,
        )
