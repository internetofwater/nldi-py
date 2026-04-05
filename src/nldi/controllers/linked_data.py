# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Linked data controller — all NLDI data endpoints."""

from typing import Annotated

from litestar import Controller, Response, get, head
from litestar.exceptions import ClientException, HTTPException, NotFoundException
from litestar.params import Dependency, Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_base_url
from ..db.navigation import NAV_DIST_DEFAULTS, NavigationModes, navigation_query, trim_nav_query
from ..db.repos import CatchmentRepository, CrawlerSourceRepository, FeatureRepository, FlowlineRepository
from ..dto import DataSource
from ..geojson import Feature, FeatureCollection, Point, parse_geometry
from ..media import MediaType
from ..negotiate import check_format
from ..pygeoapi import PyGeoAPIClient
from ..util import parse_wkt_point

# Common parameter annotations for OpenAPI documentation
SourceName = Annotated[str, Parameter(description="Data source identifier (e.g. 'wqp', 'nwissite', 'comid')")]
Identifier = Annotated[str, Parameter(description="Feature identifier within the source")]
NavMode = Annotated[str, Parameter(description="Navigation mode: UM, UT, DM, or DD")]
DataSourceParam = Annotated[str, Parameter(description="Target data source for navigated features")]
CoordsParam = Annotated[str, Parameter(description="WKT point geometry, e.g. POINT(-89.509 43.087)")]

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


def provide_pygeoapi_client() -> PyGeoAPIClient:
    """Provide PyGeoAPIClient via DI."""
    import os

    url = os.getenv("NLDI_PYGEOAPI_URL", "")
    return PyGeoAPIClient(url)


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
        """List all data sources.

        Returns a JSON array of available data sources, including the synthetic
        ``comid`` source. Each source includes a ``features`` URL for retrieving
        its features.
        """
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
    async def get_hydrolocation(
        self,
        catchment_repo: Annotated[CatchmentRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        pygeoapi_client: Annotated[PyGeoAPIClient, Dependency(skip_validation=True)],
        coords: CoordsParam = "",
    ) -> Response:
        """Return hydrologic location nearest to coordinates.

        Accepts a WKT point geometry and returns the nearest hydrologic location
        on the NHD flowline network, plus the original provided point.
        """
        if not coords:
            raise ClientException(detail="coords parameter is required.")

        try:
            lon, lat = parse_wkt_point(coords)
        except ValueError as e:
            raise ClientException(detail=str(e)) from e

        base_url = get_base_url()

        # Call pygeoapi flowtrace
        payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": str(lon)},
                {"id": "lat", "type": "text/plain", "value": str(lat)},
                {"id": "direction", "type": "text/plain", "value": "none"},
            ]
        }
        response = await pygeoapi_client.post("processes/nldi-flowtrace/execution", payload)
        snap_lon, snap_lat = response["features"][0]["properties"]["intersection_point"]
        snap_wkt = f"POINT({snap_lon} {snap_lat})"

        # Find catchment at snapped point
        catchment = await catchment_repo.get_by_point(snap_wkt)
        if not catchment:
            raise NotFoundException(detail=f"No catchment found at {coords}")
        comid = catchment.featureid

        # Compute measure and reachcode
        measure, reachcode = await flowline_repo.get_measure_and_reachcode(comid, snap_wkt)

        nav_url = f"{base_url}/linked-data/comid/{comid}/navigation"

        indexed_feature = Feature(
            geometry=Point(coordinates=(snap_lon, snap_lat)),
            properties={
                "identifier": "",
                "navigation": nav_url,
                "measure": measure,
                "reachcode": reachcode,
                "name": "",
                "source": "indexed",
                "sourceName": "Automatically indexed by the NLDI",
                "comid": comid,
                "type": "hydrolocation",
                "uri": "",
            },
        )

        provided_feature = Feature(
            geometry=Point(coordinates=(lon, lat)),
            properties={
                "identifier": "",
                "navigation": "",
                "measure": "",
                "reachcode": "",
                "name": "",
                "source": "provided",
                "sourceName": "Provided via API call",
                "comid": "",
                "type": "point",
                "uri": "",
            },
        )

        return Response(
            content=FeatureCollection(features=[indexed_feature, provided_feature]),
            status_code=200,
            media_type=MediaType.GEOJSON,
        )

    @get("/comid/position")
    async def flowline_by_position(
        self,
        catchment_repo: Annotated[CatchmentRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        coords: CoordsParam = "",
    ) -> Response:
        """Find flowline by spatial point lookup.

        Accepts a WKT point geometry (NAD83 lon/lat). Locates the catchment
        containing the point, then returns the corresponding NHD flowline.
        """
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
        source_name: SourceName,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
        feature_repo: Annotated[FeatureRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        f: str = "",
        limit: Annotated[int, Parameter(ge=0, description="Max features to return. 0 = no limit.")] = 0,
        offset: Annotated[int, Parameter(ge=0, description="Number of features to skip.")] = 0,
    ) -> Response:
        """List all features for a source.

        Returns a GeoJSON FeatureCollection of all features for the named source.
        Supports pagination via ``limit`` and ``offset`` query parameters.
        Use ``comid`` as the source name to list NHD flowlines.
        """
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
        source_name: SourceName,
        identifier: Identifier,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
        feature_repo: Annotated[FeatureRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        f: str = "",
    ) -> Response:
        """Get a single feature by source and identifier.

        Returns a GeoJSON FeatureCollection containing a single feature.
        For ``comid`` source, the identifier must be a valid NHDPlus COMID integer.
        """
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
    async def get_basin(self, source_name: SourceName, identifier: str) -> None:
        """Compute upstream basin polygon.

        Returns the aggregated drainage basin for the specified feature.
        Not yet implemented.
        """
        _not_implemented()

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
            # Get the feature's measure for trimming
            feat = await feature_repo.feature_lookup(source_name, identifier)
            measure = float(feat.measure) if feat and feat.measure else 0.0
            if not measure:
                # Estimate measure if not available — for now, skip trimming
                trim_start = False

        if trim_start:
            trim_q = trim_nav_query(mode_upper, comid, trim_tolerance or 0.0, measure)
            results = await flowline_repo.from_trimmed_nav_query(nav_q, trim_q)
            features = []
            for fl, trimmed_geojson in results:
                feature = Feature(
                    geometry=parse_geometry(trimmed_geojson) if trimmed_geojson else None,
                    properties={"nhdplus_comid": fl.nhdplus_comid},
                    id=fl.nhdplus_comid,
                )
                features.append(feature)
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
        features = [_build_source_feature(f, base_url, data_source) for f in feats]

        if exclude_geom:
            for f in features:
                f.geometry = None

        return Response(content=FeatureCollection(features=features), status_code=200, media_type=MediaType.GEOJSON)
