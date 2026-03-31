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
    """Source registry — crawler_source table.

    Each row represents a data source that the NLDI crawler has ingested.
    The source_suffix is used as the URL path segment (e.g. 'wqp', 'nwissite').
    """

    __tablename__ = "crawler_source"

    crawler_source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(500))  # Human-readable name
    source_suffix: Mapped[str] = mapped_column(String(10))  # URL path segment (e.g. 'wqp')
    source_uri: Mapped[str] = mapped_column(String(256))  # Base URI for the source
    feature_id: Mapped[str] = mapped_column(String(256))  # Column name for feature ID in source
    feature_name: Mapped[str] = mapped_column(String(256))  # Column name for feature name in source
    feature_uri: Mapped[str] = mapped_column(String(256))  # URI template for features
    feature_reach: Mapped[str] = mapped_column(String(256), nullable=True)  # Column name for reach code
    feature_measure: Mapped[str] = mapped_column(String(256), nullable=True)  # Column name for measure
    ingest_type: Mapped[str] = mapped_column(String(5), nullable=True)  # 'point' or 'reach'
    feature_type: Mapped[str] = mapped_column(String(100), nullable=True)  # Geometry type of features


class MainstemLookupModel(NLDIBaseModel):
    """Mainstem URI lookup — mainstem_lookup table.

    Maps NHDPlus COMIDs to mainstem URIs (e.g. geoconnex.us mainstem identifiers).
    """

    __tablename__ = "mainstem_lookup"

    nhdpv2_comid: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=True)  # noqa: see note below
    # NOTE: nullable=True on a PK reflects the actual DB schema. Some rows may have NULL comids.
    mainstem_id: Mapped[int] = mapped_column(Integer, nullable=True)
    uri: Mapped[str] = mapped_column(Text, nullable=True)  # Mainstem URI (e.g. geoconnex.us/ref/mainstems/...)


class FeatureSourceModel(NLDIBaseModel):
    """Feature locations — feature table.

    Each row is a point feature ingested from a crawler source, linked to
    the NHD network via comid and optionally positioned along a reach
    via reachcode and measure.
    """

    __tablename__ = "feature"

    identifier: Mapped[str] = mapped_column(String(256), primary_key=True, nullable=True)  # noqa: see note below
    # NOTE: nullable=True on PK — some features may lack identifiers in the source data.
    crawler_source_id: Mapped[int] = mapped_column(Integer, ForeignKey("crawler_source.crawler_source_id"))
    name: Mapped[str] = mapped_column(String(256), nullable=True)  # Human-readable feature name
    uri: Mapped[str] = mapped_column(String(256), nullable=True)  # Canonical URI for this feature
    location: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)  # Point geometry (NAD83)
    comid: Mapped[int] = mapped_column(Integer, ForeignKey("mainstem_lookup.nhdpv2_comid"), nullable=True)
    reachcode: Mapped[str] = mapped_column(String(14), nullable=True)  # NHD reach code
    measure: Mapped[float] = mapped_column(Float(38), nullable=True)  # Position along reach (0-100)

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
    """NHD flowlines — nhdflowline_np21 table.

    Each row is a stream segment in the NHDPlus v2.1 network.
    """

    __tablename__ = "nhdflowline_np21"

    nhdplus_comid: Mapped[int] = mapped_column(Integer, primary_key=True)  # Unique NHD segment ID
    objectid: Mapped[int] = mapped_column(Integer)  # Internal DB row ID
    permanent_identifier: Mapped[str] = mapped_column(String)  # NHD permanent identifier
    shape: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)  # LineString geometry
    fmeasure: Mapped[float] = mapped_column(Float)  # From-measure (downstream end, 0-100)
    tmeasure: Mapped[float] = mapped_column(Float)  # To-measure (upstream end, 0-100)
    reachcode: Mapped[str] = mapped_column(String)  # NHD reach code

    mainstem_lookup = relationship(
        MainstemLookupModel,
        primaryjoin=lambda: FlowlineModel.nhdplus_comid == MainstemLookupModel.nhdpv2_comid,
        foreign_keys=[nhdplus_comid],
        lazy="immediate",
    )
    mainstem: AssociationProxy[str] = association_proxy("mainstem_lookup", "uri")


class FlowlineVAAModel(NHDBaseModel):
    """Flowline value-added attributes — plusflowlinevaa_np21 table.

    Contains the network topology and routing attributes used for
    navigation CTEs in Phase 3. Only columns needed for navigation are mapped.
    """

    __tablename__ = "plusflowlinevaa_np21"

    comid: Mapped[int] = mapped_column(Integer, primary_key=True)  # NHDPlus COMID
    hydroseq: Mapped[int] = mapped_column(Integer)  # Hydrologic sequence number (routing order)
    levelpathid: Mapped[int] = mapped_column(Integer)  # Level path identifier (mainstem grouping)
    pathlength: Mapped[float] = mapped_column(Float)  # Distance to terminal point (km)
    terminalpathid: Mapped[int] = mapped_column(Integer)  # Terminal path for this network
    startflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)  # 1 = headwater
    terminalflag: Mapped[int] = mapped_column(SmallInteger, nullable=True)  # 1 = terminal (coast/sink)
    uphydroseq: Mapped[int] = mapped_column(Integer)  # Upstream mainstem hydroseq
    dnminorhyd: Mapped[int] = mapped_column(Integer)  # Downstream minor path hydroseq (diversions)
    dnhydroseq: Mapped[int] = mapped_column(Integer)  # Downstream mainstem hydroseq
    lengthkm: Mapped[float] = mapped_column(Float)  # Segment length in km
    fcode: Mapped[int] = mapped_column(Integer, nullable=True)  # NHD feature code (stream type)


class CatchmentModel(NHDBaseModel):
    """Catchment polygons — catchmentsp table.

    Each row is the local drainage area for a single NHD flowline segment.
    """

    __tablename__ = "catchmentsp"

    ogc_fid: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=True)  # Internal row ID
    the_geom: Mapped[Any] = mapped_column(geoalchemy2.Geometry, nullable=True)  # Polygon geometry
    featureid: Mapped[int] = mapped_column(Integer, nullable=True)  # Corresponding NHDPlus COMID
