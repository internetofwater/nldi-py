#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#

"""ORM mappings for tables in the nhdplus schema."""

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, SmallInteger, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from nldi.schemas.nldi_data import MainstemLookupModel

# Define the SQLAlchemy model based on the CrawlerSource Pydantic model
metadata = MetaData(schema="nhdplus")
BaseModel = declarative_base(metadata=metadata)


### TODO:  Question for Ben .. This table looks way different in the demo database. Is this the right table?
class CatchmentModel(BaseModel):
    """ORM mapping to "nhdplus.catchmentsp" table."""

    __tablename__ = "catchmentsp"

    ogc_fid = Column(Integer, primary_key=True, nullable=True)
    the_geom = Column(Geometry, nullable=True)
    gridcode = Column(Integer, nullable=True)
    featureid = Column(Integer, nullable=True)
    sourcefc = Column(String, nullable=True)
    areasqkm = Column(Float, nullable=True)
    shape_length = Column(Float, nullable=True)
    shape_area = Column(Float, nullable=True)


class FlowlineModel(BaseModel):
    """ORM mapping to "nhdplus.nhdflowline_np21" table."""

    __tablename__ = "nhdflowline_np21"

    objectid = Column(Integer)
    permanent_identifier = Column(String)
    nhdplus_comid = Column(Integer, primary_key=True)
    fdate = Column(DateTime)
    resolution = Column(Float)
    gnis_id = Column(String, nullable=True)
    gnis_name = Column(String, nullable=True)
    lengthkm = Column(Float)
    reachcode = Column(String)
    flowdir = Column(Integer)
    wbarea_permanent_identifier = Column(String, nullable=True)
    wbarea_nhdplus_comid = Column(Integer, nullable=True)
    ftype = Column(Integer)
    fcode = Column(Integer)
    reachsmdate = Column(DateTime)
    fmeasure = Column(Float)
    tmeasure = Column(Float)
    wbarea_ftype = Column(Integer, nullable=True)
    wbarea_fcode = Column(Integer, nullable=True)
    wbd_huc12 = Column(String)
    wbd_huc12_percent = Column(Float, nullable=True)
    catchment_featureid = Column(Integer, nullable=True)
    nhdplus_region = Column(String)
    nhdplus_version = Column(String)
    navigable = Column(String)
    streamlevel = Column(Integer, nullable=True)
    streamorder = Column(Integer, nullable=True)
    hydroseq = Column(Integer, nullable=True)
    levelpathid = Column(Integer, nullable=True)
    terminalpathid = Column(Integer, nullable=True)
    uphydroseq = Column(Integer, nullable=True)
    dnhydroseq = Column(Integer, nullable=True)
    closed_loop = Column(String, nullable=True)
    shape = Column(Geometry, nullable=True)


class FlowlineVAAModel(BaseModel):
    """ORM mapping to "nhdplus.plusflowlinevaa_np21" table."""

    __tablename__ = "plusflowlinevaa_np21"

    objectid = Column(Integer)
    comid = Column(Integer, primary_key=True)
    fdate = Column(DateTime)
    streamlevel = Column(SmallInteger)
    streamorder = Column(SmallInteger)
    streamcalculator = Column(SmallInteger, nullable=True)
    fromnode = Column(Integer)
    tonode = Column(Integer)
    hydroseq = Column(Integer)
    levelpathid = Column(Integer)
    pathlength = Column(Float)
    terminalpathid = Column(Integer)
    arbolatesum = Column(Float, nullable=True)
    divergence = Column(SmallInteger, nullable=True)
    startflag = Column(SmallInteger, nullable=True)
    terminalflag = Column(SmallInteger, nullable=True)
    dnlevel = Column(SmallInteger, nullable=True)
    thinnercode = Column(SmallInteger, nullable=True)
    uplevelpathid = Column(Integer)
    uphydroseq = Column(Integer)
    dnlevelpathid = Column(Integer)
    dnminorhyd = Column(Integer)
    dndraincount = Column(SmallInteger)
    dnhydroseq = Column(Integer)
    frommeas = Column(Float)
    tomeas = Column(Float)
    reachcode = Column(String)
    lengthkm = Column(Float)
    fcode = Column(Integer, nullable=True)
    rtndiv = Column(SmallInteger, nullable=True)
    outdiv = Column(SmallInteger, nullable=True)
    diveffect = Column(SmallInteger, nullable=True)
    vpuin = Column(SmallInteger, nullable=True)
    vpuout = Column(SmallInteger, nullable=True)
    travtime = Column(Float)
    pathtime = Column(Float)
    areasqkm = Column(Float, nullable=True)
    totdasqkm = Column(Float, nullable=True)
    divdasqkm = Column(Float, nullable=True)
    nhdplus_region = Column(String)
    nhdplus_version = Column(String)
    permanent_identifier = Column(String)
    reachsmdate = Column(DateTime)
    fmeasure = Column(Float)
    tmeasure = Column(Float)


FlowlineModel.mainstem_lookup = relationship(
    MainstemLookupModel,
    primaryjoin=FlowlineModel.nhdplus_comid == MainstemLookupModel.nhdpv2_comid,  # noqa
    foreign_keys=[FlowlineModel.nhdplus_comid],
    uselist=False,
)
