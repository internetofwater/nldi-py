#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""ORM mappings for tables in the nldi_data schema."""

from geoalchemy2 import Geometry
from sqlalchemy import Column, Float, Integer, MetaData, String, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Define the SQLAlchemy model based on the CrawlerSource model
metadata = MetaData(schema="nldi_data")
BaseModel = declarative_base(metadata=metadata)


class CrawlerSourceModel(BaseModel):
    """ORM mapping to "crawler_source" table."""

    __tablename__ = "crawler_source"

    crawler_source_id = Column(Integer, primary_key=True)
    source_name = Column(String(500))
    source_suffix = Column(String(10), server_default=text("lower(source_suffix)"))
    source_uri = Column(String(256))
    feature_id = Column(String(256))
    feature_name = Column(String(256))
    feature_uri = Column(String(256))
    feature_reach = Column(String(256), nullable=True)
    feature_measure = Column(String(256), nullable=True)
    ingest_type = Column(String(5), nullable=True)
    feature_type = Column(String(100), nullable=True)


class FeatureSourceModel(BaseModel):
    """ORM mapping to "feature" table."""

    __tablename__ = "feature"

    crawler_source_id = Column(Integer)
    identifier = Column(String(256), primary_key=True, nullable=True)
    name = Column(String(256), nullable=True)
    uri = Column(String(256), nullable=True)
    location = Column(Geometry, nullable=True)
    comid = Column(Integer, nullable=True)
    reachcode = Column(String(14), nullable=True)
    measure = Column(Float(38), nullable=True)


class MainstemLookupModel(BaseModel):
    """ORM mapping to "mainstem_lookup" table."""

    __tablename__ = "mainstem_lookup"
    nhdpv2_comid = Column(Integer, primary_key=True, nullable=True)
    mainstem_id = Column(Integer, nullable=True)
    uri = Column(Text, nullable=True)


FeatureSourceModel.mainstem_lookup = relationship(
    MainstemLookupModel,
    primaryjoin=FeatureSourceModel.comid == MainstemLookupModel.nhdpv2_comid,
    foreign_keys=[FeatureSourceModel.comid],
    uselist=False,
)

FeatureSourceModel.crawler_source = relationship(
    CrawlerSourceModel,
    primaryjoin=FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id,  # noqa
    foreign_keys=[FeatureSourceModel.crawler_source_id],
    uselist=False,
)
