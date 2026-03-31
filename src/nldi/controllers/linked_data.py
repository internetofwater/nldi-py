# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Linked data controller — all NLDI data endpoints."""

from typing import Annotated

from litestar import Controller, get, head
from litestar.exceptions import HTTPException
from litestar.params import Dependency
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_base_url
from ..db.repos import CrawlerSourceRepository
from ..dto import DataSource
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
    async def get_feature_by_identifier(self, source_name: str, identifier: str, f: str = "") -> None:
        """Get a single feature by source and ID."""
        _not_implemented()

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
