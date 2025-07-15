#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""ORM mappings for tables in the nldi_data schema."""

from geoalchemy2 import Geometry
from sqlalchemy import Column, Float, ForeignKey, Integer, MetaData, String, Text, text
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..mixins import GeoJSONMixin


class NLDIBaseModel(DeclarativeBase):
    metadata = MetaData(schema="nldi_data")


class CrawlerSourceModel(NLDIBaseModel):
    __tablename__ = "crawler_source"

    crawler_source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(500))
    source_suffix: Mapped[str] = mapped_column(String(10), server_default=text("lower(source_suffix)"))
    source_uri: Mapped[str] = mapped_column(String(256))
    feature_id: Mapped[str] = mapped_column(String(256))
    feature_name: Mapped[str] = mapped_column(String(256))
    feature_uri: Mapped[str] = mapped_column(String(256))
    feature_reach: Mapped[str] = mapped_column(String(256), nullable=True)
    feature_measure: Mapped[str] = mapped_column(String(256), nullable=True)
    ingest_type: Mapped[str] = mapped_column(String(5), nullable=True)
    feature_type: Mapped[str] = mapped_column(String(100), nullable=True)

    @property
    def _as_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}


class FeatureSourceModel(NLDIBaseModel, GeoJSONMixin):
    __tablename__ = "feature"

    identifier: Mapped[str] = mapped_column(String(256), primary_key=True, nullable=True)
    crawler_source_id: Mapped[int] = mapped_column(Integer, ForeignKey("crawler_source.crawler_source_id"))
    name: Mapped[str] = mapped_column(String(256), nullable=True)
    uri: Mapped[str] = mapped_column(String(256), nullable=True)
    location: Mapped[Geometry] = mapped_column(Geometry, nullable=True)
    comid: Mapped[str] = mapped_column(Integer, ForeignKey("mainstem_lookup.nhdpv2_comid"), nullable=True)
    reachcode: Mapped[str] = mapped_column(String(14), nullable=True)
    measure: Mapped[float] = mapped_column(Float(38), nullable=True)
    crawler_source = relationship(
        "CrawlerSourceModel",
        primaryjoin="FeatureSourceModel.crawler_source_id == CrawlerSourceModel.crawler_source_id",
        foreign_keys=[crawler_source_id],
        lazy="immediate",
    )
    sourceName: AssociationProxy[str] = association_proxy("crawler_source", "source_name")  # noqa: N815
    source: AssociationProxy[str] = association_proxy("crawler_source", "source_suffix")
    type: AssociationProxy[str] = association_proxy("crawler_source", "feature_type")
    mainstem_lookup = relationship(
        "MainstemLookupModel",
        primaryjoin="FeatureSourceModel.comid == MainstemLookupModel.nhdpv2_comid",
        foreign_keys=[comid],
        lazy="immediate",
    )
    mainstem: AssociationProxy[str] = association_proxy("mainstem_lookup", "uri")

    def __properties__(self, exclude: set) -> dict[str, str]:
        _props = super().__properties__(exclude)
        ## Extend the properties dict with the AssociationProxy(s) of iterest; these are not dumped with columns by default.
        if self.mainstem == "NA" or self.mainstem == "":  # possible strings to interpret as NoData for the mainstem URI.
            _mainstem = None
        else:
            _mainstem = self.mainstem
        _props.update(
            {"mainstem": _mainstem, "sourceName": self.sourceName, "source": self.source, "type": self.type}
        )
        return _props


class MainstemLookupModel(NLDIBaseModel):
    __tablename__ = "mainstem_lookup"
    nhdpv2_comid: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=True)
    mainstem_id: Mapped[int] = mapped_column(Integer, nullable=True)
    uri: Mapped[str] = mapped_column(Text, nullable=True)
