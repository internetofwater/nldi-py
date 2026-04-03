# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Linked data controller — all NLDI data endpoints."""

from typing import Annotated

from litestar import Controller, Response, get, head
from litestar.exceptions import ClientException, HTTPException, NotFoundException
from litestar.params import Dependency, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_base_url
from ..db.repos import CatchmentRepository, CrawlerSourceRepository, FeatureRepository, FlowlineRepository
from ..dto import DataSource
from ..geojson import Feature, FeatureCollection, parse_geometry
from ..media import MediaType
from ..negotiate import check_format

_ALL_PATHS = [
    "/",
    "/hydrolocation",
    "/comid/position",
    "/{source_name:str}",
    "/{source_name:str}/{identifier:str}",
    "/{source_name:str}/{identifier:str}/basin",
    "/{source_name:str}/{identifier:str}/navigation",
    "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}",
    "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/flowlines",
    "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}",
]


def _not_implemented() -> None:
    """Raise 501 for unimplemented endpoints."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


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


class LinkedDataController(Controller):
    """NLDI linked data endpoints."""

    path = "/linked-data"
    tags = ["nldi"]
    before_request = check_format

    @head(_ALL_PATHS, include_in_schema=False)
    async def handle_head(self) -> None:
        """HEAD support for all linked-data endpoints."""
        return None

    @get("/")
    async def list_sources(
        self, source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)]
    ) -> list[DataSource]:
        """List all data sources."""
        base_url = get_base_url()
        sources = await source_repo.list()
        result = [DataSource(source="comid", sourceName="NHDPlus comid", features=f"{base_url}/linked-data/comid")]
        for s in sources:
            result.append(
                DataSource(
                    source=s.source_suffix,
                    sourceName=s.source_name,
                    features=f"{base_url}/linked-data/{s.source_suffix}",
                )
            )
        return result

    @get("/hydrolocation")
    async def get_hydrolocation(self, coords: str = "") -> None:
        """Return hydrologic location nearest to coordinates."""
        _not_implemented()

    @get("/comid/position")
    async def flowline_by_position(
        self,
        catchment_repo: Annotated[CatchmentRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        coords: str = "",
    ) -> Response:
        """Find flowline by spatial point lookup."""
        if not coords:
            raise ClientException(detail="coords parameter is required.")
        base_url = get_base_url()

        catchment = await catchment_repo.get_by_point(coords)
        if not catchment:
            raise NotFoundException(detail=f"No catchment found at coords {coords}")

        comid = catchment.featureid
        flowline = await flowline_repo.get_one_or_none(nhdplus_comid=comid)
        if not flowline:
            raise NotFoundException(detail=f"No flowline for COMID {comid} at {coords}")

        nav_url = f"{base_url}/linked-data/comid/{comid}/navigation"
        feature = _build_comid_feature(flowline, base_url)
        return Response(content=FeatureCollection(features=[feature]), status_code=200, media_type=MediaType.GEOJSON)

    @get("/{source_name:str}", tags=["by_sourceid"])
    async def list_features_by_source(
        self,
        source_name: str,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
        feature_repo: Annotated[FeatureRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        f: str = "",
        limit: Annotated[int, Parameter(ge=0, description="Max features to return. 0 = no limit.")] = 0,
        offset: Annotated[int, Parameter(ge=0, description="Number of features to skip.")] = 0,
    ) -> Response:
        """List all features for a source."""
        base_url = get_base_url()

        if source_name.lower() == "comid":
            items = await flowline_repo.list_all(limit=limit, offset=offset)
            features = [_build_comid_feature(fl, base_url) for fl in items]
        else:
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                raise NotFoundException(detail=f"No such source: {source_name}")
            items = await feature_repo.list_by_source(source_name, limit=limit, offset=offset)
            features = [_build_source_feature(feat, base_url, source_name) for feat in items]

        fc = FeatureCollection(features=features)
        return Response(content=fc, status_code=200, media_type=MediaType.GEOJSON)

    @get("/{source_name:str}/{identifier:str}", tags=["by_sourceid"])
    async def get_feature_by_identifier(
        self,
        source_name: str,
        identifier: str,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
        feature_repo: Annotated[FeatureRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        f: str = "",
    ) -> Response:
        """Get a single feature by source and ID."""
        base_url = get_base_url()

        if source_name.lower() == "comid":
            try:
                comid = int(identifier)
            except ValueError as e:
                raise ClientException(detail=f"Not a valid comid: {identifier}") from e
            flowline = await flowline_repo.get_one_or_none(nhdplus_comid=comid)
            if not flowline:
                raise NotFoundException(detail=f"COMID {identifier} not found.")
            feature = _build_comid_feature(flowline, base_url)
        else:
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                raise NotFoundException(detail=f"No such source: {source_name}")
            feat = await feature_repo.feature_lookup(source_name, identifier)
            if not feat:
                raise NotFoundException(detail=f"Feature {identifier} not found in source {source_name}.")
            feature = _build_source_feature(feat, base_url, source_name)

        return Response(content=FeatureCollection(features=[feature]), status_code=200, media_type=MediaType.GEOJSON)

    @get("/{source_name:str}/{identifier:str}/basin", tags=["by_sourceid"])
    async def get_basin(self, source_name: str, identifier: str) -> None:
        """Compute upstream basin polygon."""
        _not_implemented()

    @get("/{source_name:str}/{identifier:str}/navigation", tags=["by_sourceid"])
    async def get_navigation_modes(
        self,
        source_name: str,
        identifier: str,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
    ) -> dict:
        """Return navigation mode URLs."""
        base_url = get_base_url()
        if source_name.lower() != "comid":
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                raise NotFoundException(detail=f"No such source: {source_name}")
        nav_url = f"{base_url}/linked-data/{source_name}/{identifier}/navigation"
        return {
            "upstreamMain": f"{nav_url}/UM",
            "upstreamTributaries": f"{nav_url}/UT",
            "downstreamMain": f"{nav_url}/DM",
            "downstreamDiversions": f"{nav_url}/DD",
        }

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}", tags=["by_sourceid"])
    async def get_navigation_info(
        self,
        source_name: str,
        identifier: str,
        nav_mode: str,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
    ) -> list[dict]:
        """List data sources available for navigation."""
        valid_modes = {"UM", "UT", "DM", "DD"}
        if nav_mode.upper() not in valid_modes:
            raise ClientException(
                detail=f"Invalid navigation mode: {nav_mode}. Must be one of {', '.join(sorted(valid_modes))}."
            )
        base_url = get_base_url()
        if source_name.lower() != "comid":
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                raise NotFoundException(detail=f"No such source: {source_name}")
        nav_url = f"{base_url}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}"
        result = [{"source": "Flowlines", "sourceName": "NHDPlus flowlines", "features": f"{nav_url}/flowlines"}]
        sources = await source_repo.list()
        for s in sources:
            result.append(
                {
                    "source": s.source_suffix,
                    "sourceName": s.source_name,
                    "features": f"{nav_url}/{s.source_suffix.lower()}",
                }
            )
        return result

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/flowlines", tags=["by_sourceid"])
    async def get_flowline_navigation(self, source_name: str, identifier: str, nav_mode: str) -> None:
        """Navigate flowlines."""
        _not_implemented()

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}", tags=["by_sourceid"])
    async def get_feature_navigation(self, source_name: str, identifier: str, nav_mode: str, data_source: str) -> None:
        """Navigate features of a data source."""
        _not_implemented()
