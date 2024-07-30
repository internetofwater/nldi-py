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
from sqlalchemy import MetaData, Column, Integer, String, Float, text, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Define the SQLAlchemy model based on the CrawlerSource model
metadata = MetaData(schema='nldi_data')
BaseModel = declarative_base(metadata=metadata)


class CrawlerSourceModel(BaseModel):
    __tablename__ = 'crawler_source'

    crawler_source_id = Column(Integer, primary_key=True)
    source_name = Column(String(500))
    source_suffix = Column(String(10),
                           server_default=text('lower(source_suffix)'))
    source_uri = Column(String(256))
    feature_id = Column(String(256))
    feature_name = Column(String(256))
    feature_uri = Column(String(256))
    feature_reach = Column(String(256), nullable=True)
    feature_measure = Column(String(256), nullable=True)
    ingest_type = Column(String(5), nullable=True)
    feature_type = Column(String(100), nullable=True)


class FeatureSourceModel(BaseModel):
    __tablename__ = 'feature'

    crawler_source_id = Column(Integer)
    identifier = Column(String(256), primary_key=True, nullable=True)
    name = Column(String(256), nullable=True)
    uri = Column(String(256), nullable=True)
    location = Column(Geometry, nullable=True)
    comid = Column(Integer, nullable=True)
    reachcode = Column(String(14), nullable=True)
    measure = Column(Float(38), nullable=True)


class MainstemLookupModel(BaseModel):
    __tablename__ = 'mainstem_lookup'

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
