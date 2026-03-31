# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""ORM models mapping to NLDI and NHDPlus database tables.

These are pure data/object models — no serialization logic.
Serialization to GeoJSON or other formats belongs in the DTO layer.
"""

from typing import Any

import geoalchemy2
from sqlalchemy import Float, ForeignKey, Integer, MetaData, SmallInteger, String, Text
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ---------------------------------------------------------------------------
# nldi_data schema
# ---------------------------------------------------------------------------


class NLDIBaseModel(DeclarativeBase):
    """Base for tables in the nldi_data schema."""

    metadata = MetaData(schema="nldi_data")


class CrawlerSourceModel(NLDIBaseModel):
    """Source registry — crawler_source table."""

    __tablename__ = "crawler_source"

    crawler_source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(500))
    source_suffix: Mapped[str] = mapped_column(String(10))
    source_uri: Mapped[str] = mapped_column(String(256))
    feature_id: Mapped[str] = mapped_column(String(256))
    feature_name: Mapped[str] = mapped_column(String(256))
    feature_uri: Mapped[str] = mapped_column(String(256))
    feature_reach: Mapped[str] = mapped_column(String(256), nullable=True)
    feature_measure: Mapped[str] = mapped_column(String(256), nullable=True)
    ingest_type: Mapped[str] = mapped_column(String(5), nullable=True)
    feature_type: Mapped[str] = mapped_column(String(100), nullable=True)


class MainstemLookupModel(NLDIBaseModel):
    """Mainstem URI lookup — mainstem_lookup table."""

    __tablename__ = "mainstem_lookup"

    nhdpv2_comid: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=True)
    mainstem_id: Mapped[int] = mapped_column(Integer, nullable=True)
    uri: Mapped[str] = mapped_column(Text, nullable=True)


class FeatureSourceModel(NLDIBaseModel):
    """Feature locations — feature table."""

    __tablename__ = "feature"

    identifier: Mapped[str] = mapped_column(String(256), primary_key=True, nullable=True)
    crawler_source_id: Mapped[int] = mapped_column(Integer, ForeignKey("crawler_source.crawler_source_id"))
    name: Mapped[str] = mapped_column(String(256), nullable=True)
    uri: Mapped[str] = mapped_column(String(256), nullable=True)
    location: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)
    comid: Mapped[int] = mapped_column(Integer, ForeignKey("mainstem_lookup.nhdpv2_comid"), nullable=True)
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


# ---------------------------------------------------------------------------
# nhdplus schema
# ---------------------------------------------------------------------------


class NHDBaseModel(DeclarativeBase):
    """Base for tables in the nhdplus schema."""

    metadata = MetaData(schema="nhdplus")


class FlowlineModel(NHDBaseModel):
    """NHD flowlines — nhdflowline_np21 table."""

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
        primaryjoin=lambda: FlowlineModel.nhdplus_comid == MainstemLookupModel.nhdpv2_comid,
        foreign_keys=[nhdplus_comid],
        lazy="immediate",
    )
    mainstem: AssociationProxy[str] = association_proxy("mainstem_lookup", "uri")


class FlowlineVAAModel(NHDBaseModel):
    """Flowline value-added attributes — plusflowlinevaa_np21 table.

    Used for navigation CTEs in Phase 3.
    """

    __tablename__ = "plusflowlinevaa_np21"

    comid: Mapped[int] = mapped_column(Integer, primary_key=True)
    hydroseq: Mapped[int] = mapped_column(Integer)
    levelpathid: Mapped[int] = mapped_column(Integer)
    pathlength: Mapped[float] = mapped_column(Float)
    terminalpathid: Mapped[int] = mapped_column(Integer)
    startflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    terminalflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    uphydroseq: Mapped[int] = mapped_column(Integer)
    dnminorhyd: Mapped[int] = mapped_column(Integer)
    dnhydroseq: Mapped[int] = mapped_column(Integer)
    lengthkm: Mapped[float] = mapped_column(Float)
    fcode: Mapped[int] = mapped_column(Integer, nullable=True)


class CatchmentModel(NHDBaseModel):
    """Catchment polygons — catchmentsp table."""

    __tablename__ = "catchmentsp"

    ogc_fid: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=True)
    the_geom: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)
    featureid: Mapped[int] = mapped_column(Integer, nullable=True)
