# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Lookup endpoints — sources, features, position, hydrolocation."""

from typing import Annotated

import msgspec
from litestar import Controller, Response, get, head
from litestar.params import Dependency, Parameter

from ...db.models import FlowlineModel
from ...dto import DataSource
from ...geojson import Feature, FeatureCollection, Point, parse_geometry
from ...jsonld import to_jsonld_graph, to_jsonld_single
from ...util import parse_wkt_point
from . import (
    CatchmentRepository,
    CoordsParam,
    CrawlerSourceRepository,
    FeatureRepository,
    FlowlineRepository,
    Identifier,
    MediaType,
    PyGeoAPIClient,
    SourceName,
    _build_comid_feature,
    _build_source_feature,
    _resolve_comid,
    check_format,
    get_base_url,
)


def _respond_features(features: list[Feature], f: str = "") -> Response:
    """Return features as GeoJSON or JSON-LD depending on f parameter."""
    if f == "jsonld":
        feature_dicts = [msgspec.to_builtins(feat) for feat in features]
        if len(feature_dicts) == 1:
            content = to_jsonld_single(feature_dicts[0])
        else:
            content = to_jsonld_graph(feature_dicts)
        return Response(content=content, status_code=200, media_type=MediaType.JSONLD)
    return Response(content=FeatureCollection(features=features), status_code=200, media_type=MediaType.GEOJSON)


_LOOKUP_PATHS = [
    "/",
    "/hydrolocation",
    "/comid/position",
    "/{source_name:str}",
    "/{source_name:str}/{identifier:str}",
]


class LookupController(Controller):
    """Source and feature lookup endpoints."""

    path = "/linked-data"
    tags = ["nldi"]
    before_request = check_format

    @head(_LOOKUP_PATHS, include_in_schema=False)
    async def handle_head(self) -> None:
        """HEAD support for lookup endpoints."""
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
            from litestar.exceptions import ClientException

            raise ClientException(detail="coords parameter is required.")

        try:
            lon, lat = parse_wkt_point(coords)
        except ValueError as e:
            from litestar.exceptions import ClientException

            raise ClientException(detail=str(e)) from e

        base_url = get_base_url()
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

        from litestar.exceptions import NotFoundException

        catchment = await catchment_repo.get_by_point(snap_wkt)
        if not catchment:
            raise NotFoundException(detail=f"No catchment found at {coords}")
        comid = catchment.featureid

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
            from litestar.exceptions import ClientException

            raise ClientException(detail="coords parameter is required.")
        try:
            parse_wkt_point(coords)
        except ValueError as e:
            from litestar.exceptions import ClientException

            raise ClientException(detail=str(e))
        base_url = get_base_url()
        catchment = await catchment_repo.get_by_point(coords)
        if not catchment:
            from litestar.exceptions import NotFoundException

            raise NotFoundException(detail=f"No catchment found at coords {coords}")
        comid = catchment.featureid
        flowline = await flowline_repo.get_one_or_none(FlowlineModel.nhdplus_comid == comid)
        if not flowline:
            from litestar.exceptions import NotFoundException

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
                from litestar.exceptions import NotFoundException

                raise NotFoundException(detail=f"No such source: {source_name}")
            items = await feature_repo.list_by_source(source_name, limit=limit, offset=offset)
            features = [_build_source_feature(feat, base_url, source_name) for feat in items]
        return _respond_features(features, f)

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
                from litestar.exceptions import ClientException

                raise ClientException(detail=f"Not a valid comid: {identifier}") from e
            flowline = await flowline_repo.get_one_or_none(FlowlineModel.nhdplus_comid == comid)
            if not flowline:
                from litestar.exceptions import NotFoundException

                raise NotFoundException(detail=f"COMID {identifier} not found.")
            feature = _build_comid_feature(flowline, base_url)
        else:
            source = await source_repo.get_by_suffix(source_name)
            if not source:
                from litestar.exceptions import NotFoundException

                raise NotFoundException(detail=f"No such source: {source_name}")
            feat = await feature_repo.feature_lookup(source_name, identifier)
            if not feat:
                from litestar.exceptions import NotFoundException

                raise NotFoundException(detail=f"Feature {identifier} not found in source {source_name}.")
            feature = _build_source_feature(feat, base_url, source_name)
        return _respond_features([feature], f)
