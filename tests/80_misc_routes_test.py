#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""
Random other endpoints.

- [ ] Endpoint(s)
    - [X] GET f"{API_PREFIX}/"
    - [x] GET f"{API_PREFIX}/linked-data/hydrolocation?{coords}"
      - requires pygeoapi
    - [ ] GET f"{API_PREFIX}/linked-data/{source_name}/{identifier}/basin"
      - requires pygeoapi
      - Send request to pygeoapi to calculate basin; return result as FeatureCollection
      - 5xx error if pygeoapi error
      - 404 if source_name or identifier not found
"""

import psycopg
import pytest

from nldi.db.schemas import struct_geojson
from nldi.domain.linked_data.services import basin, catchment, pygeoapi

from . import API_PREFIX


# region Services
@pytest.mark.order(82)
@pytest.mark.unittest
def test_pygeoapi_service_instantiates(dbsession_containerized):
    svc = pygeoapi.PyGeoAPIService(session=dbsession_containerized)
    assert svc.flowtrace_service_endpoint is not None


@pytest.mark.order(82)
@pytest.mark.integration
async def test_pygeoapi_service_hydrolocation(dbsession_containerized):
    svc = pygeoapi.PyGeoAPIService(session=dbsession_containerized)
    actual = await svc.hydrolocation_by_coords("POINT(-89.22401470690966 42.82769689708948)")
    expected = {  ## according to https://labs.waterdata.usgs.gov/api/nldi/linked-data/hydrolocation?f=json&coords=POINT%28-89.22401470690966%2042.82769689708948%29
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-89.2240173681987, 42.8277996494545]},
                "properties": {
                    "identifier": "",
                    "navigation": "https://labs.waterdata.usgs.gov/api/nldi/linked-data/comid/13297332/navigation",
                    "measure": "48.23773299682034",
                    "reachcode": "07090002007792",
                    "name": "",
                    "source": "indexed",
                    "sourceName": "Automatically indexed by the NLDI",
                    "comid": "13297332",
                    "type": "hydrolocation",
                    "uri": "",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-89.2240147069097, 42.8276968970895]},
                "properties": {
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
            },
        ],
    }
    # NOTE: actual is a msgspec struct at this point. Comparing to a dict of similar structure
    assert str(actual[0].properties["measure"]) == expected["features"][0]["properties"]["measure"]
    assert str(actual[0].properties["reachcode"]) == expected["features"][0]["properties"]["reachcode"]
    assert str(actual[0].properties["comid"]) == expected["features"][0]["properties"]["comid"]
    assert actual[0].geometry["coordinates"][0] == pytest.approx(
        expected["features"][0]["geometry"]["coordinates"][0], abs=1e-6
    )
    assert actual[0].geometry["coordinates"][1] == pytest.approx(
        expected["features"][0]["geometry"]["coordinates"][1], abs=1e-6
    )


@pytest.mark.order(82)
@pytest.mark.integration
async def test_pygeoapi_service_splitcatchment(dbsession_containerized):
    svc = pygeoapi.PyGeoAPIService(session=dbsession_containerized)
    actual = await svc.splitcatchment_at_coords("POINT(-89.22401470690966 42.82769689708948)")
    assert actual["type"] == "Feature"
    assert actual["geometry"]["type"].endswith("Polygon")  ## could be Polygon or MultiPolygon
    ## TODO:  Verify the computed values are correct.


@pytest.mark.order(83)
@pytest.mark.integration
async def test_catchment_by_comid(dbsession_containerized):
    svc = catchment.CatchmentService(session=dbsession_containerized)
    actual = await svc.get_drainage_basin_by_comid(13297166, simplified=False)
    assert actual is not None


@pytest.mark.order(83)
@pytest.mark.integration
async def test_basin_get_from_id(dbsession_containerized):
    svc = basin.BasinService(session=dbsession_containerized, pygeoapi_url="https://api.water.usgs.gov/nldi/pygeoapi")
    assert svc is not None
    features = await svc.get_by_id(identifier="USGS-05427930", source_name="wqp", simplified=False, split=False)
    assert isinstance(features, list)
    assert len(features) == 1
    f = features[0]
    assert isinstance(f, struct_geojson.Feature)


# region Endpoints


@pytest.mark.order(85)
@pytest.mark.unittest
def test_api_get_root(ls_client_localhost) -> None:
    r = ls_client_localhost.get(f"{API_PREFIX}?f=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


@pytest.mark.order(89)
@pytest.mark.integration
def test_api_get_hydrolocation(ls_client_containerized) -> None:
    r = ls_client_containerized.get(
        f"{API_PREFIX}/linked-data/hydrolocation?f=json&coords=POINT(-89.22401470690966 42.82769689708948)"
    )
    assert r.status_code == 200
    actual = r.json()
    assert actual["type"] == "FeatureCollection"
    assert len(actual["features"]) == 2


@pytest.mark.order(89)
@pytest.mark.integration
def test_api_get_hydrolocation_flask(f_client_containerized) -> None:
    r = f_client_containerized.get(
        f"{API_PREFIX}/linked-data/hydrolocation?f=json&coords=POINT(-89.22401470690966 42.82769689708948)"
    )
    assert r.status_code == 200
    actual = r.json
    assert actual["type"] == "FeatureCollection"
    assert len(actual["features"]) == 2
