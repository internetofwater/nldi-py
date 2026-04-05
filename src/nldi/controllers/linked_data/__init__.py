# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Linked data controllers — shared helpers and DI providers."""

import json
from typing import Annotated

from litestar import Response
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import Dependency, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_base_url
from ...db.repos import CatchmentRepository, CrawlerSourceRepository, FeatureRepository, FlowlineRepository
from ...geojson import Feature, FeatureCollection, Point, parse_geometry
from ...media import MediaType
from ...negotiate import check_format
from ...pygeoapi import PyGeoAPIClient

# DI providers


async def provide_source_repo(db_session: AsyncSession) -> CrawlerSourceRepository:
    """Provide CrawlerSourceRepository via DI."""
    return CrawlerSourceRepository(session=db_session)


async def provide_feature_repo(db_session: AsyncSession) -> FeatureRepository:
    """Provide FeatureRepository via DI."""
    return FeatureRepository(session=db_session)


async def provide_flowline_repo(db_session: AsyncSession) -> FlowlineRepository:
    """Provide FlowlineRepository via DI."""
    return FlowlineRepository(session=db_session)


async def provide_catchment_repo(db_session: AsyncSession) -> CatchmentRepository:
    """Provide CatchmentRepository via DI."""
    return CatchmentRepository(session=db_session)


def provide_pygeoapi_client() -> PyGeoAPIClient:
    """Provide PyGeoAPIClient via DI."""
    import os

    url = os.getenv("NLDI_PYGEOAPI_URL", "")
    return PyGeoAPIClient(url)


# Shared helpers


async def _resolve_comid(source_name, identifier, source_repo, feature_repo, flowline_repo) -> int:
    """Resolve a source/identifier pair to a COMID."""
    if source_name.lower() == "comid":
        try:
            return int(identifier)
        except ValueError as e:
            raise ClientException(detail=f"Not a valid comid: {identifier}") from e
    source = await source_repo.get_by_suffix(source_name)
    if not source:
        raise NotFoundException(detail=f"No such source: {source_name}")
    feat = await feature_repo.feature_lookup(source_name, identifier)
    if not feat:
        raise NotFoundException(detail=f"Feature {identifier} not found in source {source_name}.")
    if not feat.comid:
        raise NotFoundException(detail=f"No comid for feature {identifier} in source {source_name}.")
    return int(feat.comid)


def _build_nav_flowline_feature(flowline) -> Feature:
    """Build a minimal GeoJSON Feature for navigation flowline results."""
    return Feature(
        geometry=parse_geometry(str(flowline.shape)) if flowline.shape else None,
        properties={"nhdplus_comid": flowline.nhdplus_comid},
        id=flowline.nhdplus_comid,
    )


def _build_comid_feature(flowline, base_url: str) -> Feature:
    """Build a GeoJSON Feature from a FlowlineModel."""
    comid = flowline.nhdplus_comid
    return Feature(
        geometry=parse_geometry(str(flowline.shape)) if flowline.shape else None,
        properties={
            "identifier": str(comid),
            "navigation": f"{base_url}/linked-data/comid/{comid}/navigation",
            "source": "comid",
            "sourceName": "NHDPlus comid",
            "comid": comid,
        },
        id=comid,
    )


def _build_source_feature(feat, base_url: str, source_name: str) -> Feature:
    """Build a GeoJSON Feature from a FeatureSourceModel."""
    return Feature(
        geometry=parse_geometry(str(feat.location)) if feat.location else None,
        properties={
            "identifier": feat.identifier,
            "navigation": f"{base_url}/linked-data/{source_name}/{feat.identifier}/navigation",
            "name": feat.name,
            "source": feat.source_suffix_proxy,
            "sourceName": feat.source_name_proxy,
            "comid": feat.comid if feat.comid else None,
            "type": feat.feature_type_proxy,
            "uri": feat.uri,
            "reachcode": feat.reachcode or None,
            "mainstem": feat.mainstem if feat.mainstem and feat.mainstem != "NA" else None,
        },
        id=feat.identifier,
    )


def _not_implemented() -> None:
    """Raise 501 for unimplemented endpoints."""
    from litestar.exceptions import HTTPException

    raise HTTPException(status_code=501, detail="Not yet implemented")


# Common parameter type aliases
SourceName = Annotated[str, Parameter(description="Data source identifier (e.g. 'wqp', 'nwissite', 'comid')")]
Identifier = Annotated[str, Parameter(description="Feature identifier within the source")]
NavMode = Annotated[str, Parameter(description="Navigation mode: UM, UT, DM, or DD")]
DataSourceParam = Annotated[str, Parameter(description="Target data source for navigated features")]
CoordsParam = Annotated[str, Parameter(description="WKT point geometry, e.g. POINT(-89.509 43.087)")]
