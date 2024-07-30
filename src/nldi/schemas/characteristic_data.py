# =================================================================
#
# Author: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

from geoalchemy2 import Geometry
from sqlalchemy import MetaData, Column, Integer, SmallInteger, Numeric
from sqlalchemy.ext.declarative import declarative_base

# Define the SQLAlchemy model based on the CrawlerSource Pydantic model
metadata = MetaData(schema="characteristic_data")
BaseModel = declarative_base(metadata=metadata)


class CatchmentModel(BaseModel):
    __tablename__ = "catchmentsp"

    ogc_fid = Column(Integer, primary_key=True)
    featureid = Column(Integer, nullable=True)
    the_geom = Column(Geometry, nullable=True)


class FlowlineVAAModel(BaseModel):
    __tablename__ = "plusflowlinevaa_np21"

    comid = Column(Integer)
    hydroseq = Column(Numeric(11), primary_key=True)
    startflag = Column(SmallInteger, nullable=True)
    dnhydroseq = Column(Numeric(11))
    dnminorhyd = Column(Numeric(11))
    pathlength = Column(Numeric(11), nullable=True)
