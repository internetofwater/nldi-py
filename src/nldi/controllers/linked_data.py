# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Linked data controller — all NLDI data endpoints."""

from typing import Annotated

from litestar import Controller, Response, get, head
from litestar.exceptions import ClientException, HTTPException, NotFoundException
from litestar.params import Dependency
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_base_url
from ..db.repos import CrawlerSourceRepository, FeatureRepository, FlowlineRepository
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
    async def flowline_by_position(self, coords: str = "") -> None:
        """Find flowline by spatial point lookup."""
        _not_implemented()

    @get("/{source_name:str}", tags=["by_sourceid"])
    async def list_features_by_source(self, source_name: str, f: str = "") -> None:
        """List all features for a source."""
        _not_implemented()

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
        nav_url = f"{base_url}/linked-data/{source_name}/{identifier}/navigation"

        if source_name.lower() == "comid":
            try:
                comid = int(identifier)
            except ValueError as e:
                raise ClientException(detail=f"Not a valid comid: {identifier}") from e
            flowline = await flowline_repo.get(comid)
            if not flowline:
                raise NotFoundException(detail=f"COMID {identifier} not found.")
            feature = Feature(
                geometry=parse_geometry(str(flowline.shape_geojson)) if hasattr(flowline, "shape_geojson") else None,
                properties={
                    "identifier": str(flowline.nhdplus_comid),
                    "navigation": nav_url,
                    "source": "comid",
                    "sourceName": "NHDPlus comid",
                    "comid": flowline.nhdplus_comid,
                },
                id=flowline.nhdplus_comid,
            )
        else:
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                raise NotFoundException(detail=f"No such source: {source_name}")
            feat = await feature_repo.feature_lookup(source_name, identifier)
            if not feat:
                raise NotFoundException(detail=f"Feature {identifier} not found in source {source_name}.")
            feature = Feature(
                geometry=None,  # TODO: geometry serialization from DB in integration
                properties={
                    "identifier": feat.identifier,
                    "navigation": nav_url,
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

        fc = FeatureCollection(features=[feature])
        return Response(content=fc, status_code=200, media_type=MediaType.GEOJSON)

    @get("/{source_name:str}/{identifier:str}/basin", tags=["by_sourceid"])
    async def get_basin(self, source_name: str, identifier: str) -> None:
        """Compute upstream basin polygon."""
        _not_implemented()

    @get("/{source_name:str}/{identifier:str}/navigation", tags=["by_sourceid"])
    async def get_navigation_modes(self, source_name: str, identifier: str) -> None:
        """Return navigation mode URLs."""
        _not_implemented()

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}", tags=["by_sourceid"])
    async def get_navigation_info(self, source_name: str, identifier: str, nav_mode: str) -> None:
        """List data sources available for navigation."""
        _not_implemented()

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/flowlines", tags=["by_sourceid"])
    async def get_flowline_navigation(self, source_name: str, identifier: str, nav_mode: str) -> None:
        """Navigate flowlines."""
        _not_implemented()

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}", tags=["by_sourceid"])
    async def get_feature_navigation(self, source_name: str, identifier: str, nav_mode: str, data_source: str) -> None:
        """Navigate features of a data source."""
        _not_implemented()
