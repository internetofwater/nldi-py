#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#

"""ORM mappings for tables in the nhdplus schema."""

from datetime import datetime
from functools import cached_property
from typing import Any

import geoalchemy2
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, SmallInteger, String
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..mixins import GeoJSONMixin
from . import struct_geojson
from .nldi_data import MainstemLookupModel


class NHDBaseModel(DeclarativeBase):
    """
    Base model for all tables in the ``nhdplus`` schema.

    Note that in most of these models, we are only declaring a subset of the columns
    found in the authoritative/complete NHD+ data model. We only use a small subset of those
    attributes, so we only declare those columns that we need in these models.
    """

    metadata = MetaData(schema="nhdplus")


class CatchmentModel(NHDBaseModel, GeoJSONMixin):
    """ORM mapping to "nhdplus.catchmentsp" table."""

    __tablename__ = "catchmentsp"

    ogc_fid: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=True)
    the_geom: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)
    featureid: Mapped[int] = mapped_column(Integer, nullable=True)


class FlowlineModel(NHDBaseModel, GeoJSONMixin):
    """ORM mapping to "nhdplus.nhdflowline_np21" table."""

    __tablename__ = "nhdflowline_np21"

    nhdplus_comid: Mapped[int] = mapped_column(Integer, primary_key=True)
    objectid: Mapped[int] = mapped_column(Integer)
    permanent_identifier: Mapped[str] = mapped_column(String)
    shape: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)
    fmeasure: Mapped[float] = mapped_column(Float)
    tmeasure: Mapped[float] = mapped_column(Float)
    reachcode: Mapped[str] = mapped_column(String)

    mainstem_lookup = relationship(
        MainstemLookupModel,
        primaryjoin=nhdplus_comid == MainstemLookupModel.nhdpv2_comid,  # noqa
        foreign_keys=[nhdplus_comid],
        lazy="immediate",
    )
    mainstem: AssociationProxy[str] = association_proxy("mainstem_lookup", "uri")

    def __properties__(self, exclude: set) -> dict[str, str]:
        _props = super().__properties__(exclude)
        ## Extend the properties dict with the AssociationProxy(s) of interest; these are not dumped with columns by default.
        if self.mainstem == "NA" or self.mainstem == "":  # possible strings to interpret as NoData for the mainstem URI.
            _mainstem = None
        else:
            _mainstem = self.mainstem
        _props.update({"mainstem": _mainstem, "sourceName": "NHDPlus comid", "source": "comid"})
        return _props


class FlowlineVAAModel(NHDBaseModel):
    """ORM mapping to "nhdplus.plusflowlinevaa_np21" table."""

    ## TODO: Verify that we will be using all of these columns; drop unusued from the model.
    __tablename__ = "plusflowlinevaa_np21"

    # objectid: Mapped[int] = mapped_column(Integer)
    comid: Mapped[int] = mapped_column(Integer, primary_key=True)
    # fdate: Mapped[datetime] = mapped_column(DateTime)
    # streamlevel: Mapped[int] = mapped_column(SmallInteger)
    # streamorder: Mapped[int] = mapped_column(SmallInteger)
    # streamcalculator: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # fromnode: Mapped[int] = mapped_column(Integer)
    # tonode: Mapped[int] = mapped_column(Integer)
    hydroseq: Mapped[int] = mapped_column(Integer)
    levelpathid: Mapped[int] = mapped_column(Integer)
    pathlength: Mapped[float] = mapped_column(Float)
    terminalpathid: Mapped[int] = mapped_column(Integer)
    # arbolatesum: Mapped[float] = mapped_column(Float, nullable=True)
    # divergence: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    startflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    terminalflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # dnlevel: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # thinnercode: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # uplevelpathid: Mapped[int] = mapped_column(Integer)
    uphydroseq: Mapped[int] = mapped_column(Integer)
    # dnlevelpathid: Mapped[int] = mapped_column(Integer)
    dnminorhyd: Mapped[int] = mapped_column(Integer)
    # dndraincount: Mapped[int] = mapped_column(SmallInteger)
    dnhydroseq: Mapped[int] = mapped_column(Integer)
    # frommeas: Mapped[float] = mapped_column(Float)
    # tomeas: Mapped[float] = mapped_column(Float)
    # reachcode: Mapped[str] = mapped_column(String)
    lengthkm: Mapped[float] = mapped_column(Float)
    fcode: Mapped[int] = mapped_column(Integer, nullable=True)
    # rtndiv: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # outdiv: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # diveffect: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # vpuin: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # vpuout: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # travtime: Mapped[float] = mapped_column(Float)
    # pathtime: Mapped[float] = mapped_column(Float)
    # areasqkm: Mapped[float] = mapped_column(Float, nullable=True)
    # totdasqkm: Mapped[float] = mapped_column(Float, nullable=True)
    # divdasqkm: Mapped[float] = mapped_column(Float, nullable=True)
    # nhdplus_region: Mapped[str] = mapped_column(String)
    # nhdplus_version: Mapped[str] = mapped_column(String)
    # permanent_identifier: Mapped[str] = mapped_column(String)
    # reachsmdate: Mapped[datetime] = mapped_column(DateTime)
    # fmeasure: Mapped[float] = mapped_column(Float)
    # tmeasure: Mapped[float] = mapped_column(Float)
