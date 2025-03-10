#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# See the full copyright notice in LICENSE.md


import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Self

import httpx
import shapely
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from nldi.db.schemas.nhdplus import CatchmentModel, FlowlineModel

from .... import util
from ....db.schemas import struct_geojson
from . import CatchmentService, FlowlineService, NavigationService


class PyGeoAPIService:
    """Provides a mechanism for proxying requests to a PyGeoAPI instance running elsewhere."""

    DEFAULT_PYGEOAPI_URL = "https://labs-beta.waterdata.usgs.gov/api/nldi/pygeoapi"
    HTTP_TIMEOUT = 20  # seconds
    DEFAULT_PROPS = {
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
    }

    def __init__(self, session: AsyncSession, pygeoapi_url: str = DEFAULT_PYGEOAPI_URL):
        self._service_url = pygeoapi_url
        self._session = session
        self.flowline_svc = FlowlineService(session=self._session)
        self.catchment_svc = CatchmentService(session=self._session)

    @classmethod
    @asynccontextmanager
    async def new(
        cls,
        session: AsyncSession,
    ) -> AsyncIterator[Self]:
        if session:
            yield cls(session=session)

    @classmethod
    def _post_to_external_service(cls, url: str, data: dict = {}, timeout: int = 0) -> dict:
        _to = timeout if timeout > 0 else cls.HTTP_TIMEOUT
        # LOGGER.debug(f"{__class__.__name__} Sending POST (timeout={_to}) to: {url}")
        try:
            with httpx.Client(verify=False) as client:
                r = client.post(url, data=json.dumps(data), timeout=_to).raise_for_status()
                response = r.json()
        except httpx.HTTPStatusError as err:  # pragma: no cover
            raise RuntimeError(f"Error connecting to service {url}")
        except json.JSONDecodeError as err:  # pragma: no cover
            raise RuntimeError(f"Error parsing JSON response from {url}")
        return response

    @property
    def flowtrace_service_endpoint(self) -> str:
        """Return the fully qualified URL for the flowtrace service endpoint."""
        return util.url_join(self._service_url, "processes", "nldi-flowtrace", "execution")

    @property
    def splitcatchment_service_endpoint(self) -> str:
        """Return the url for the split catchment service endpoint."""
        return util.url_join(self._service_url, "processes", "nldi-splitcatchment", "execution")

    async def hydrolocation_by_coords(self, coords: str, base_url: str = "/") -> struct_geojson.FeatureCollection:
        """Get a hydrolocation by coordinates."""
        point_shp = shapely.from_wkt(coords)
        request_payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": str(point_shp.x)},
                {"id": "lat", "type": "text/plain", "value": str(point_shp.y)},
                {"id": "direction", "type": "text/plain", "value": "none"},
            ]
        }

        response = self._post_to_external_service(self.flowtrace_service_endpoint, data=request_payload)
        (lon, lat) = response["features"][0]["properties"]["intersection_point"]  # noqa
        flowtrace_return_pt_wkt = f"POINT({lon} {lat})"

        _catchment = await self.catchment_svc.get_by_wkt_point(flowtrace_return_pt_wkt)
        if not _catchment:
            raise KeyError("Catchment not found.")
        nhdplus_comid = _catchment.featureid

        nav_url = util.url_join(base_url, "linked-data", "comid", nhdplus_comid, "navigation")

        measure = (
            FlowlineModel.fmeasure
            + (
                1
                - sqlalchemy.func.ST_LineLocatePoint(
                    FlowlineModel.shape, sqlalchemy.func.ST_GeomFromText(flowtrace_return_pt_wkt, 4269)
                )
            )
            * (FlowlineModel.tmeasure - FlowlineModel.fmeasure)
        ).label("measure")

        computed_reach = await self.flowline_svc.get_one_or_none(
            FlowlineModel.nhdplus_comid == nhdplus_comid,
            statement=sqlalchemy.select(FlowlineModel.reachcode),
        )
        computed_measure = await self.flowline_svc.get_one_or_none(
            FlowlineModel.nhdplus_comid == nhdplus_comid,
            statement=sqlalchemy.select(measure),
        )
        if not computed_measure:
            raise KeyError(f"No measure found for: {coords}.")

        _return_feature_collection = struct_geojson.FeatureCollection(
            features=[
                struct_geojson.Feature(
                    geometry={"type": "Point", "coordinates": [lon, lat]},
                    properties={
                        "identifier": "",
                        "navigation": nav_url,
                        "measure": computed_measure,
                        "reachcode": computed_reach,
                        "name": "",
                        "source": "indexed",
                        "sourceName": "Automatically indexed by the NLDI",
                        "comid": nhdplus_comid,
                        "type": "hydrolocation",
                        "uri": "",
                    },
                ),
                struct_geojson.Feature(
                    geometry=point_shp.__geo_interface__,
                    properties=self.DEFAULT_PROPS,
                ),
            ],
        )
        return _return_feature_collection

    async def splitcatchment_at_coords(self, coords: str) -> dict:
        point_shp = shapely.from_wkt(coords)

        request_payload = {
            "inputs": [
                {"id": "lon", "type": "text/plain", "value": str(point_shp.x)},
                {"id": "lat", "type": "text/plain", "value": str(point_shp.y)},
                {"id": "upstream", "type": "text/plain", "value": "true"},
            ]
        }

        response = self._post_to_external_service(
            self.splitcatchment_service_endpoint,
            data=request_payload,
            timeout=2 * self.HTTP_TIMEOUT,  ## give the split algorithm a bit more time to work.
        )

        # Search for feature with id "mergedCatchment" or "drainageBasin"
        _to_return = None
        for feature in response["features"]:
            if feature["id"] == "mergedCatchment" or feature["id"] == "drainageBasin":
                # The ID changes from "mergedCatchment" to "drainageBasin" with this commit in Aug, 2024:
                # https://code.usgs.gov/wma/nhgf/toolsteam/nldi-flowtools/-/commit/08b4042cbfe34d2c22dfac83120c0629d9ad444f
                # Trapping both of these possible IDs now to handle the case when that change makes it to production.
                feature.pop("id")
                _to_return = feature

        return _to_return  # caller is expecting an iterable
        # previous versions yielded the return value here, allowing caller to loop over a generator producing
        # just the single value. Returning the single feature instead represents a breaking change -- caller must
        # make their own list if they need this feature in that form.


async def pygeoapi_svc(db_session: AsyncSession) -> AsyncGenerator[NavigationService, None]:
    """Provider function as part of the dependency-injection mechanism."""
    async with PyGeoAPIService.new(session=db_session) as service:
        yield service
