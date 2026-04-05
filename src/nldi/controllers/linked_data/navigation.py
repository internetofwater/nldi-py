# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Navigation endpoints — modes, info, flowline nav, feature nav."""

from typing import Annotated

import msgspec
from litestar import Controller, Response, get, head
from litestar.exceptions import ClientException
from litestar.params import Dependency, Parameter

from ...db.navigation import NAV_DIST_DEFAULTS, NavigationModes, navigation_query, trim_nav_query
from ...jsonld import to_jsonld_graph
from . import (
    CrawlerSourceRepository,
    DataSourceParam,
    Feature,
    FeatureCollection,
    FeatureRepository,
    FlowlineRepository,
    Identifier,
    MediaType,
    NavMode,
    SourceName,
    _build_nav_flowline_feature,
    _build_source_feature,
    _resolve_comid,
    check_format,
    get_base_url,
    parse_geometry,
)

_NAV_PATHS = [
    "/{source_name:str}/{identifier:str}/navigation",
    "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}",
    "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/flowlines",
    "/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}",
]


class NavigationController(Controller):
    """Navigation endpoints."""

    path = "/linked-data"
    tags = ["nldi"]
    before_request = check_format

    @head(_NAV_PATHS, include_in_schema=False)
    async def handle_head(self) -> None:
        """HEAD support for navigation endpoints."""
        return None

    @get("/{source_name:str}/{identifier:str}/navigation", tags=["by_sourceid"])
    async def get_navigation_modes(
        self,
        source_name: SourceName,
        identifier: Identifier,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
    ) -> dict:
        """Return navigation mode URLs.

        Returns a JSON object with URLs for each navigation mode
        (UM, UT, DM, DD) from the specified starting feature.
        """
        base_url = get_base_url()
        if source_name.lower() != "comid":
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                from litestar.exceptions import NotFoundException

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
        source_name: SourceName,
        identifier: Identifier,
        nav_mode: NavMode,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
    ) -> list[dict]:
        """List data sources available for a navigation mode.

        Returns a JSON array of data sources whose features can be found
        along the specified navigation. Flowlines are always listed first.
        The ``nav_mode`` must be one of: UM, UT, DM, DD.
        """
        valid_modes = {"UM", "UT", "DM", "DD"}
        if nav_mode.upper() not in valid_modes:
            raise ClientException(
                detail=f"Invalid navigation mode: {nav_mode}. Must be one of {', '.join(sorted(valid_modes))}."
            )
        base_url = get_base_url()
        if source_name.lower() != "comid":
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                from litestar.exceptions import NotFoundException

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
    async def get_flowline_navigation(
        self,
        source_name: SourceName,
        identifier: Identifier,
        nav_mode: NavMode,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
        feature_repo: Annotated[FeatureRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        distance: float | None = None,
        trim_start: Annotated[bool, Parameter(query="trimStart")] = False,
        trim_tolerance: Annotated[float, Parameter(query="trimTolerance")] = 0.0,
        exclude_geom: Annotated[bool, Parameter(query="excludeGeometry")] = False,
    ) -> Response:
        """Navigate flowlines from a starting point.

        Returns a GeoJSON FeatureCollection of NHD flowlines along the
        navigation path. Supports ``trimStart`` to clip the starting
        flowline geometry and ``excludeGeometry`` to omit geometry data.
        """
        mode_upper = nav_mode.upper()
        if mode_upper not in NavigationModes.__members__:
            raise ClientException(
                detail=f"Invalid navigation mode: {nav_mode}. Must be one of {', '.join(NavigationModes)}."
            )

        if trim_start and source_name.lower() == "comid":
            raise ClientException(detail="Cannot use trimStart with comid source.")

        comid = await _resolve_comid(source_name, identifier, source_repo, feature_repo, flowline_repo)
        dist = distance if distance is not None else NAV_DIST_DEFAULTS.get(NavigationModes(mode_upper), 100)

        nav_q = navigation_query(mode_upper, comid=comid, distance=dist)

        if trim_start:
            feat = await feature_repo.feature_lookup(source_name, identifier)
            measure = float(feat.measure) if feat and feat.measure else 0.0
            if not measure:
                trim_start = False

        if trim_start:
            trim_q = trim_nav_query(mode_upper, comid, trim_tolerance or 0.0, measure)
            results = await flowline_repo.from_trimmed_nav_query(nav_q, trim_q)
            features = []
            for fl, trimmed_geojson in results:
                features.append(
                    Feature(
                        geometry=parse_geometry(trimmed_geojson) if trimmed_geojson else None,
                        properties={"nhdplus_comid": fl.nhdplus_comid},
                        id=fl.nhdplus_comid,
                    )
                )
        else:
            flowlines = await flowline_repo.from_nav_query(nav_q)
            features = [_build_nav_flowline_feature(fl) for fl in flowlines]

        if exclude_geom:
            for f in features:
                f.geometry = None

        return Response(content=FeatureCollection(features=features), status_code=200, media_type=MediaType.GEOJSON)

    @get("/{source_name:str}/{identifier:str}/navigation/{nav_mode:str}/{data_source:str}", tags=["by_sourceid"])
    async def get_feature_navigation(
        self,
        source_name: SourceName,
        identifier: Identifier,
        nav_mode: NavMode,
        data_source: DataSourceParam,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
        feature_repo: Annotated[FeatureRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        distance: float | None = None,
        exclude_geom: Annotated[bool, Parameter(query="excludeGeometry")] = False,
        f: str = "",
    ) -> Response:
        """Navigate features of a data source.

        Returns a GeoJSON FeatureCollection of features from the specified
        data source found along the navigation path. Supports
        ``excludeGeometry`` to omit geometry data.
        """
        mode_upper = nav_mode.upper()
        if mode_upper not in NavigationModes.__members__:
            raise ClientException(
                detail=f"Invalid navigation mode: {nav_mode}. Must be one of {', '.join(NavigationModes)}."
            )

        comid = await _resolve_comid(source_name, identifier, source_repo, feature_repo, flowline_repo)
        dist = distance if distance is not None else NAV_DIST_DEFAULTS.get(NavigationModes(mode_upper), 100)
        base_url = get_base_url()

        nav_q = navigation_query(mode_upper, comid=comid, distance=dist)
        feats = await feature_repo.from_nav_query(data_source, nav_q)
        features = [_build_source_feature(f_item, base_url, data_source) for f_item in feats]

        if exclude_geom:
            for feat in features:
                feat.geometry = None

        if f == "jsonld":
            feature_dicts = [msgspec.to_builtins(feat) for feat in features]
            return Response(content=to_jsonld_graph(feature_dicts), status_code=200, media_type=MediaType.JSONLD)
        return Response(content=FeatureCollection(features=features), status_code=200, media_type=MediaType.GEOJSON)
