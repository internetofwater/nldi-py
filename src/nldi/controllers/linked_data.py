# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Linked data controller — all NLDI data endpoints."""

from litestar import Controller, Request, route
from litestar.exceptions import HTTPException

from ..helpers import head_response
from ..negotiate import check_format


def _not_implemented() -> None:
    """Raise 501 for unimplemented endpoints."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


class LinkedDataController(Controller):
    """NLDI linked data endpoints."""

    path = "/linked-data"
    tags = ["nldi"]
    before_request = check_format

    @route("/", http_method=["GET", "HEAD"])
    async def list_sources(self, request: Request) -> None:
        """List all data sources."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route("/hydrolocation", http_method=["GET", "HEAD"])
    async def get_hydrolocation(self, request: Request, coords: str = "") -> None:
        """Return hydrologic location nearest to coordinates."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route("/comid/position", http_method=["GET", "HEAD"])
    async def flowline_by_position(self, request: Request, coords: str = "") -> None:
        """Find flowline by spatial point lookup."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route("/{source_name:str}", http_method=["GET", "HEAD"], tags=["by_sourceid"])
    async def list_features_by_source(self, request: Request, source_name: str, f: str = "") -> None:
        """List all features for a source."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route("/{source_name:str}/{identifier:str}", http_method=["GET", "HEAD"], tags=["by_sourceid"])
    async def get_feature_by_identifier(self, request: Request, source_name: str, identifier: str, f: str = "") -> None:
        """Get a single feature by source and ID."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route("/{source_name:str}/{identifier:str}/basin", http_method=["GET", "HEAD"], tags=["by_sourceid"])
    async def get_basin(self, request: Request, source_name: str, identifier: str) -> None:
        """Compute upstream basin polygon."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route("/{source_name:str}/{identifier:str}/navigation", http_method=["GET", "HEAD"], tags=["by_sourceid"])
    async def get_navigation_modes(self, request: Request, source_name: str, identifier: str) -> None:
        """Return navigation mode URLs."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route(
        "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}",
        http_method=["GET", "HEAD"],
        tags=["by_sourceid"],
    )
    async def get_navigation_info(self, request: Request, source_name: str, identifier: str, nav_mode: str) -> None:
        """List data sources available for navigation."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route(
        "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/flowlines",
        http_method=["GET", "HEAD"],
        tags=["by_sourceid"],
    )
    async def get_flowline_navigation(self, request: Request, source_name: str, identifier: str, nav_mode: str) -> None:
        """Navigate flowlines."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()

    @route(
        "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}",
        http_method=["GET", "HEAD"],
        tags=["by_sourceid"],
    )
    async def get_feature_navigation(
        self, request: Request, source_name: str, identifier: str, nav_mode: str, data_source: str
    ) -> None:
        """Navigate features of a data source."""
        if request.method == "HEAD":
            return head_response()
        _not_implemented()
