#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""
Controllers and route handlers for the "system" (i.e. infrastructure) endpoints.

System endpoints include the essential furniture ("/", "/robots.txt", "/favicon.ico")
as well as system information endpoints -- healthcheck being one example.
"""

from collections.abc import AsyncGenerator
from copy import deepcopy
from typing import Annotated, Any, Literal, TypeVar

import geoalchemy2
import litestar
import sqlalchemy
from advanced_alchemy.exceptions import NotFoundError
from advanced_alchemy.extensions.litestar.dto import SQLAlchemyDTO
from litestar.exceptions import HTTPException
from litestar.params import Parameter
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_501_NOT_IMPLEMENTED,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from nldi.db.schemas import struct_geojson
from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel
from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel

from ... import LOGGER, util
from . import services

NAD83_SRID = 4269


class HTML_JSON_Exception(Exception):
    pass


def html_to_json_redirect(
    request: litestar.Request, exc: Exception
) -> litestar.response.Response[litestar.MediaType.HTML]:
    _new_q = deepcopy(request.url.query_params)
    _new_q["f"] = "json"
    new_url = request.url.with_replacements(query=_new_q)

    return litestar.response.Response(
        media_type=litestar.MediaType.HTML,
        content=f"""
                <html>
                An HTML representation is not available for this resource.
                <br/>
                If you would like to see the data as JSON, <a href="{new_url}">click here</a>.
                </html>
        """,
        status_code=200,
    )


def response_format_check(request: litestar.Request) -> Any:
    LOGGER.info("pre-checking request...")
    preferred_type = request.accept.best_match([litestar.MediaType.HTML], default=litestar.MediaType.HTML)
    a = request.accept
    q = request.query_params
    fmt = q.get("f")
    if fmt == "json":
        LOGGER.info("JSON explicitly specified")
        return
    if fmt == "html" or a.accepts("text/html"):
        raise HTML_JSON_Exception


def base_url(state: litestar.datastructures.State) -> str:
    return state.cfg.server.base_url


# region Controller
class LinkedDataController(litestar.Controller):
    """Controller/route-handler for all of the Linked Data endpoints"""

    tags = ["comid"]
    path = "/linked-data"
    before_request = response_format_check
    exception_handlers = {
        HTML_JSON_Exception: html_to_json_redirect,
    }
    dependencies = {
        "sources_svc": litestar.di.Provide(services.crawler_source_svc),
        "flowline_svc": litestar.di.Provide(services.flowline_svc),
        "catchment_svc": litestar.di.Provide(services.catchment_svc),
        "feature_svc": litestar.di.Provide(services.feature_svc),
        "navigation_svc": litestar.di.Provide(services.navigation_svc),
        "pygeoapi_svc": litestar.di.Provide(services.pygeoapi_svc),
        "base_url": litestar.di.Provide(base_url, sync_to_thread=False),
    }

    @litestar.get("/", summary="List all sources.")
    async def list_sources(self, sources_svc: services.CrawlerSourceService) -> list[CrawlerSourceModel]:
        """
        Produce a list of all sources used to construct the features table within the NLDI database.

        Each item in the returned list includes metadata about the original source and how features are
        retrieved from it.
        """
        src_list = await sources_svc.list()
        return list(src_list)

    @litestar.get("/comid/{comid:int}", summary="Lookup NHD Flowline by ComID")
    async def flowline_by_comid(
        self, flowline_svc: services.FlowlineService, comid: int, base_url: str
    ) -> struct_geojson.FeatureCollection:
        """Lookup flowline by attribute search on the COMID property."""
        try:
            flowline_feature = await flowline_svc.get_feature(
                comid,
                xtra_props={"navigation": util.url_join(base_url, "comid", comid, "navigation")},
            )
        except NotFoundError:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"COMID {comid} not found.")
        return struct_geojson.FeatureCollection(features=[flowline_feature])

    @litestar.get("/comid/position", summary="Lookup NHD Flowline by position/point")
    async def flowline_by_position(
        self,
        coords: str,
        flowline_svc: services.FlowlineService,
        catchment_svc: services.CatchmentService,
        base_url: str,
    ) -> struct_geojson.FeatureCollection:
        """Find flowline by spatial search."""
        # Step 1: Get the COMID of the catchment polygon holding the point.
        try:
            catchment = await catchment_svc.get_by_wkt_point(coords)
            comid = int(catchment.featureid)
        except ValueError as e:
            raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except NotFoundError as e:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))

        # Step2: use that catchment's COMID to lookup flowline
        flowline_feature = await flowline_svc.get_feature(
            comid,
            xtra_props={"navigation": util.url_join(base_url, "comid", comid, "navigation")},
        )
        return struct_geojson.FeatureCollection(
            features=[flowline_feature],
        )

    @litestar.get("/hydrolocation")
    async def get_hydrolocation(
        self, pygeoapi_svc: services.PyGeoAPIService, coords: str, base_url: str
    ) -> struct_geojson.FeatureCollection:
        returnval = await pygeoapi_svc.hydrolocation_by_coords(coords, base_url=base_url)
        return returnval

    # region Routes Per-Source:

    @litestar.get(path=["/{src_suffix:str}", "/{src_suffix:str}/{identifier:str}"])
    async def all_feature_by_src(
        self,
        src_suffix: str,
        feature_svc: services.FeatureService,
        sources_svc: services.CrawlerSourceService,
        base_url: str,
        identifier: Annotated[str | None, Parameter(required=False)] = None,
    ) -> litestar.response.Stream:
        """
        Return one or more features from a given source.

        This endpoint supports a "list mode" if no identifier given, returning all features from the source. If
        an identifier is given, only that feature is returned (assuming it is found in the table).  In the case
        where an identifier is provided but not found, a 404 is returned.
        """
        try:
            if identifier:
                _ = await feature_svc.feature_lookup(src_suffix, identifier)
            else:
                _ = await sources_svc.get_by_suffix(src_suffix)
        except NotFoundError:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)

        return litestar.response.Stream(
            feature_svc.feature_collection_stream(source_suffix=src_suffix, identifier=identifier, base_url=base_url),
            media_type=litestar.MediaType.JSON,
        )

    @litestar.get("/{source_name:str}/{identifier:str}/basin")  # TODO: implement
    async def get_basin(self, source_name: str, identifier: str, request: litestar.Request) -> dict[str, Any]:
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED,
            detail="Not Implemented",
            extra={
                "path": request.url.path,
                "handler": str(request.route_handler),
                "query_params": dict(request.query_params),
                "path_params": request.path_params,
            },
        )

    @litestar.get(
        "/{source_name:str}/{identifier:str}/navigation", summary="Show endpoints for each navigation lookup mode."
    )
    async def get_navigation_modes(
        self, source_name: str, identifier: str, sources_svc: services.CrawlerSourceService, base_url: str
    ) -> dict[str, str]:
        """
        Identify the endpoints for each of the navigation modes possible from this source and feature.

        This will return a HTTP 404 (Not Found) status if the source name is not found in the database.
        """
        if not sources_svc.suffix_exists(source_name):
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"No such source: {source_name}")

        nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")
        content = {
            "upstreamMain": util.url_join(nav_url, "UM"),
            "upstreamTributaries": util.url_join(nav_url, "UT"),
            "downstreamMain": util.url_join(nav_url, "DM"),
            "downstreamDiversions": util.url_join(nav_url, "DD"),
        }
        return content

    @litestar.get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}")
    async def get_navigation_info(
        self,
        source_name: str,
        identifier: str,
        nav_mode: str,
        sources_svc: services.CrawlerSourceService,
        base_url: str,
    ) -> list[dict[str, str]]:
        if not sources_svc.suffix_exists(source_name):
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"No such source: {source_name}")

        nav_url = util.url_join(base_url, "linked-data", source_name, identifier, "navigation")

        content = [
            {
                "source": "Flowlines",
                "sourceName": "NHDPlus flowlines",
                "features": util.url_join(nav_url, nav_mode, "flowlines"),
            }
        ]
        for source in await sources_svc.list():
            src_id = source.source_suffix
            content.append(
                {
                    "source": src_id,
                    "sourceName": source.source_name,
                    "features": util.url_join(nav_url, nav_mode, src_id.lower()),
                }
            )
        return content

    @litestar.get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/flowlines")
    async def get_flowline_navigation(
        self,
        navigation_svc: services.NavigationService,
        source_name: str,
        identifier: str,
        nav_mode: str,
        distance: float,
        trimStart: bool = False,
    ) -> struct_geojson.FeatureCollection:
        try:
            features = await navigation_svc.walk_flowlines(source_name, identifier, nav_mode, distance, True)
        except NotFoundError as e:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

        return struct_geojson.FeatureCollection(features=features)

    @litestar.get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}")
    async def get_feature_navigation(
        self,
        navigation_svc: services.NavigationService,
        source_name: str,
        identifier: str,
        nav_mode: str,
        data_source: str,
        distance: float,
    ) -> struct_geojson.FeatureCollection:
        try:
            features = await navigation_svc.walk_features(source_name, identifier, nav_mode, data_source, distance)
        except NotFoundError as e:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

        return struct_geojson.FeatureCollection(features=features)
