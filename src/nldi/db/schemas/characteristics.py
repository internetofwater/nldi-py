#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""ORM Configuration for interacting with the characteristic_data schema."""

import geoalchemy2
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, SmallInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_mixin, mapped_column, relationship

from ..mixins import GeoJSONMixin
from . import struct_geojson


class CharacteristicsBaseModel(DeclarativeBase):
    """
    Base model for all tables in the ``nhdplus`` schema.

    Note that in most of these models, we are only declaring a subset of the columns
    found in the authoritative/complete NHD+ data model. We only use a small subset of those
    attributes, so we only declare those columns that we need in these models.
    """

    metadata = MetaData(schema="nhdplus")


class CharacteristicMetaData(CharacteristicsBaseModel):
    __tablename__ = "characteristic_metadata"

    characteristic_id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    characteristic_description: Mapped[str] = mapped_column(String)
    UnicodeTranslateErrordataset_label: Mapped[str] = mapped_column(String)
    dataset_url: Mapped[str] = mapped_column(String)
    theme_label: Mapped[str] = mapped_column(String)
    theme_url: Mapped[str] = mapped_column(String)
    characteristic_type: Mapped[str] = mapped_column(String)


@declarative_mixin
class CharBaseTable:
    """Defines common column names for several of the characteristics table"""

    comid: Mapped[int] = mapped_column(Integer, primary_key=True)
    characteristic_id: Mapped[str] = mapped_column(String, primary_key=True)
    characteristic_value: Mapped[float] = mapped_column(Float)
    percent_nodata: Mapped[int] = mkapped_column(Integer)


class DivergenceCharacteristics(CharBaseTable, CharacteristicsBaseModel):
    __tablename__ = "divergence_routed_characteristics"


class LocalCharacteristics(CharBaseTable, CharacteristicsBaseModel):
    __tablename__ = "local_catchment_characteristics"


class TotalAccCharacteristics(CharBaseTable, CharacteristicsBaseModel):
    __tablename__ = "total_accumulated_characteristics"


class CatchmentModel(GeoJSONMixin, CharacteristicsBaseModel):
    __tablename__ = "catchmentsp"

    ogc_fid: Mapped[int] = mapped_column(Integer, primary_key=True)
    the_geom: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)
    featureid: Mapped[int] = mapped_column(Integer, nullable=True)


class FlowlineVAAModel(CharacteristicsBaseModel):
    __tablename__ = "plusflowlinevaa_np21"

    # objectid: Mapped[int] = mapped_column(Integer)
    comid: Mapped[int] = mapped_column(Integer, primary_key=True)
    # fdate: Mapped[datetime] = mapped_column(DateTime)
    # streamlevel: Mapped[int] = mapped_column(SmallInteger)
    # streamorder: Mapped[int] = mapped_column(SmallInteger)
    # streamcalculator: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # fromnode: Mapped[int] = mapped_column(Integer)
    # tonode: Mapped[int] = mapped_column(Integer)
    # hydroseq: Mapped[int] = mapped_column(Integer)
    # levelpathid: Mapped[int] = mapped_column(Integer)
    pathlength: Mapped[float] = mapped_column(Float)
    # terminalpathid: Mapped[int] = mapped_column(Integer)
    # arbolatesum: Mapped[float] = mapped_column(Float, nullable=True)
    # divergence: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    startflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # terminalflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # dnlevel: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # thinnercode: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    # uplevelpathid: Mapped[int] = mapped_column(Integer)
    # uphydroseq: Mapped[int] = mapped_column(Integer)
    # dnlevelpathid: Mapped[int] = mapped_column(Integer)
    dnminorhyd: Mapped[int] = mapped_column(Integer)
    # dndraincount: Mapped[int] = mapped_column(SmallInteger)
    dnhydroseq: Mapped[int] = mapped_column(Integer)
    # frommeas: Mapped[float] = mapped_column(Float)
    # tomeas: Mapped[float] = mapped_column(Float)
    # reachcode: Mapped[str] = mapped_column(String)
    # lengthkm: Mapped[float] = mapped_column(Float)
    # fcode: Mapped[int] = mapped_column(Integer, nullable=True)
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
