# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2024-present USGS
"""Basin endpoint — upstream drainage basin polygon."""

import json
from typing import Annotated

from litestar import Controller, Response, get, head
from litestar.exceptions import ClientException, NotFoundException
from litestar.params import Dependency, Parameter

from ...db.navigation import basin_query
from . import (
    CatchmentRepository,
    CrawlerSourceRepository,
    Feature,
    FeatureCollection,
    FeatureRepository,
    FlowlineRepository,
    Identifier,
    MediaType,
    PyGeoAPIClient,
    SourceName,
    _resolve_comid,
    check_format,
    parse_geometry,
)

_BASIN_PATHS = [
    "/{source_name:str}/{identifier:str}/basin",
]

SPLIT_CATCHMENT_THRESHOLD = 200  # meters


class BasinController(Controller):
    """Basin endpoint."""

    path = "/linked-data"
    tags = ["nldi"]
    before_request = check_format

    @head(_BASIN_PATHS, include_in_schema=False)
    async def handle_head(self) -> None:
        """HEAD support for basin endpoint."""
        return None

    @get("/{source_name:str}/{identifier:str}/basin", tags=["by_sourceid"])
    async def get_basin(
        self,
        source_name: SourceName,
        identifier: Identifier,
        source_repo: Annotated[CrawlerSourceRepository, Dependency(skip_validation=True)],
        feature_repo: Annotated[FeatureRepository, Dependency(skip_validation=True)],
        flowline_repo: Annotated[FlowlineRepository, Dependency(skip_validation=True)],
        catchment_repo: Annotated[CatchmentRepository, Dependency(skip_validation=True)],
        pygeoapi_client: Annotated[PyGeoAPIClient, Dependency(skip_validation=True)],
        simplified: Annotated[bool, Parameter(description="Simplify basin geometry")] = True,
        split_catchment: Annotated[
            bool, Parameter(query="splitCatchment", description="Split catchment at feature point")
        ] = False,
    ) -> Response:
        """Compute upstream basin polygon.

        Returns the aggregated drainage basin for the specified feature
        as a GeoJSON FeatureCollection with a single Polygon/MultiPolygon.
        Optionally splits the local catchment at the feature's position.
        """
        if split_catchment and source_name.lower() == "comid":
            raise ClientException(detail="Cannot use splitCatchment with comid source.")

        comid = await _resolve_comid(source_name, identifier, source_repo, feature_repo, flowline_repo)

        if split_catchment and source_name.lower() != "comid":
            point = await self._find_point_on_flowline(
                identifier, source_name, flowline_repo, feature_repo, pygeoapi_client
            )
            if not point:
                raise NotFoundException(detail="Unable to retrieve point on flowline for catchment splitting.")

            lon, lat = point
            result = await pygeoapi_client.splitcatchment(lon, lat)
            if not result or "geometry" not in result:
                raise NotFoundException(detail="Split catchment service returned no result.")

            feature = Feature(geometry=parse_geometry(json.dumps(result["geometry"])), properties={}, id=0)
        else:
            nav_q = basin_query(comid)
            geojson_str = await catchment_repo.get_drainage_basin(nav_q, simplified=simplified)
            if not geojson_str:
                raise NotFoundException(detail=f"No basin found for {source_name}/{identifier}")
            feature = Feature(geometry=parse_geometry(geojson_str), properties={}, id=0)

        return Response(content=FeatureCollection(features=[feature]), status_code=200, media_type=MediaType.GEOJSON)

    async def _find_point_on_flowline(
        self, identifier, source_name, flowline_repo, feature_repo, pygeoapi_client
    ) -> tuple[float, float] | None:
        """Find a point on the flowline for split catchment. Three fallback strategies."""
        # Plan A: interpolate from measure
        point = await flowline_repo.feat_get_point_along_flowline(identifier, source_name)
        if point:
            return point

        # Plan B: nearest point if within threshold
        try:
            distance = await flowline_repo.feat_get_distance_from_flowline(identifier, source_name)
            if distance is not None and distance <= SPLIT_CATCHMENT_THRESHOLD:
                point = await flowline_repo.feat_get_nearest_point_on_flowline(identifier, source_name)
                if point:
                    return point
        except (LookupError, TypeError, ValueError):
            pass

        # Plan C: pygeoapi flowtrace
        try:
            feat = await feature_repo.feature_lookup(source_name, identifier)
            if feat and feat.location:
                geom = json.loads(str(feat.location))
                lon, lat = geom["coordinates"]
                payload = {
                    "inputs": [
                        {"id": "lon", "type": "text/plain", "value": str(lon)},
                        {"id": "lat", "type": "text/plain", "value": str(lat)},
                        {"id": "direction", "type": "text/plain", "value": "none"},
                    ]
                }
                response = await pygeoapi_client.post("processes/nldi-flowtrace/execution", payload)
                snap_lon, snap_lat = response["features"][0]["properties"]["intersection_point"]
                return (snap_lon, snap_lat)
        except (LookupError, TypeError, ValueError, KeyError):
            pass

        return None
