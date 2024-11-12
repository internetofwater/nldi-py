#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""Characteristic Data"""


## NOTE:   DEPRECATED -- we are not doing characteristic data any longer.

from sqlalchemy import Column, Integer, MetaData, Numeric, SmallInteger
from sqlalchemy.ext.declarative import declarative_base

# Define the SQLAlchemy model based on the CrawlerSource Pydantic model
metadata = MetaData(schema="characteristic_data")
BaseModel = declarative_base(metadata=metadata)


class CatchmentModel(BaseModel):
    """ORM mapping to "catchmentsp" table."""

    __tablename__ = "catchmentsp"

    ogc_fid = Column(Integer, primary_key=True)
    featureid = Column(Integer, nullable=True)
    the_geom = Column(Geometry, nullable=True)


class FlowlineVAAModel(BaseModel):
    """ORM mapping to "plusflowlinevaa_np21" table."""

    __tablename__ = "plusflowlinevaa_np21"

    comid = Column(Integer)
    hydroseq = Column(Numeric(11), primary_key=True)
    startflag = Column(SmallInteger, nullable=True)
    dnhydroseq = Column(Numeric(11))
    dnminorhyd = Column(Numeric(11))
    pathlength = Column(Numeric(11), nullable=True)
