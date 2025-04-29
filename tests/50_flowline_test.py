#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

# + = Done
# - = Not Done
# o = In-Process
# X = FAILING

"""
Flowline Lookups -- Finding "FlowLine" features using "comid" source.

- [+] FlowlineModel Repository
- [+] FlowlineModel Service
- [+] CatchmentModel Service
- [+] COMID Endpoint(s)
    - [+] GET f"{API_PREFIX}/linked-data/comid/{comid}"
      - [+] Valid Lookup
      - [+] Notfound key
      - [+] non-int comid
    - [+] GET f"{API_PREFIX}/linked-data/comid/position?{coords}"

"""

import geoalchemy2
import pytest
from litestar.exceptions import HTTPException

from nldi.server.linked_data import repos, services

from . import API_PREFIX


# region: repository
@pytest.mark.order(50)
@pytest.mark.unittest
async def test_flowline_repo_get(dbsession_containerized) -> None:
    comid = 13293396  # < NOTE: at the repo level, we expect the search param to be an int, as that is the dtype of the primary-key column.
    flowline_repo = repos.FlowlineRepository(session=dbsession_containerized)
    healthy = await flowline_repo.check_health(flowline_repo.session)
    assert healthy

    actual = await flowline_repo.get(comid)
    assert actual is not None


# region: service layer
@pytest.mark.order(50)
@pytest.mark.unittest
async def test_flowline_svc_get(dbsession_containerized) -> None:
    comid = "13293396"  # The *SERVICE* will try to cast the search value to an int before calling the repo.
    flowline_svc = services.FlowlineService(session=dbsession_containerized)
    actual = await flowline_svc.get(comid)
    assert actual is not None

    comid = int(comid)  # < But should still work as an int.
    flowline_svc = services.FlowlineService(session=dbsession_containerized)
    actual = await flowline_svc.get(comid)
    assert actual is not None


@pytest.mark.order(51)
@pytest.mark.unittest
async def test_flowline_svc_get_bad_id(dbsession_containerized) -> None:
    comid = "x13293396"  # ID can't be cast to int.
    flowline_svc = services.FlowlineService(session=dbsession_containerized)
    with pytest.raises(ValueError):
        actual = await flowline_svc.get(comid)


@pytest.mark.order(51)
@pytest.mark.unittest
async def test_flowline_svc_get_feature(dbsession_containerized) -> None:
    comid = "13293396"  # ID can't be cast to int.
    flowline_svc = services.FlowlineService(session=dbsession_containerized)
    actual = await flowline_svc.get_feature(comid)
    assert actual is not None


@pytest.mark.order(52)
@pytest.mark.unittest
async def test_catchment_svc_by_geom(dbsession_containerized) -> None:
    catch_svc = services.CatchmentService(session=dbsession_containerized)
    point = geoalchemy2.WKTElement("POINT(-89.22401470690966 42.82769689708948)", srid=4269)
    catchment = await catch_svc.get_by_geom(point)
    assert catchment is not None
    assert catchment.featureid == 13297332


@pytest.mark.order(52)
@pytest.mark.unittest
async def test_catchment_svc_by_coords(dbsession_containerized) -> None:
    catch_svc = services.CatchmentService(session=dbsession_containerized)
    catchment = await catch_svc.get_by_wkt_point("POINT(-89.22401470690966 42.82769689708948)")
    assert catchment is not None
    assert catchment.featureid == 13297332


@pytest.mark.order(52)
@pytest.mark.unittest
async def test_catchment_svc_by_coords_mangled(dbsession_containerized) -> None:
    catch_svc = services.CatchmentService(session=dbsession_containerized)
    with pytest.raises(ValueError):
        catchment = await catch_svc.get_by_wkt_point("PT(-89.22401470690966 42.82769689708948)")


# region: flask endpoints
@pytest.mark.order(55)
@pytest.mark.unittest
def test_flowline_get_by_comid(f_client_testdb) -> None:
    comid = "13293396"  # << This COMID is known to be in the test database
    r = f_client_testdb.get(f"{API_PREFIX}/linked-data/comid/{comid}?f=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")

    actual = r.json  # Should return a feature collection as JSON
    assert actual["type"] == "FeatureCollection"
    features = actual["features"]
    assert isinstance(features, list)
    assert len(features) == 1


@pytest.mark.order(55)
@pytest.mark.unittest
def test_flowline_get_by_comid_notfound(f_client_testdb) -> None:
    comid = "00000000"  # << bogus comid
    r = f_client_testdb.get(f"{API_PREFIX}/linked-data/comid/{comid}?f=json")
    assert r.status_code == 404


@pytest.mark.order(55)
@pytest.mark.unittest
def test_flowline_get_by_comid_bad_id(f_client_testdb) -> None:
    comid = "x13293396"  # << incorrect type
    r = f_client_testdb.get(f"{API_PREFIX}/linked-data/comid/{comid}?f=json")
    # NOTE: The router/parser will recognize this comid as an invalid type and return NOTFOUND before our handler is called.
    assert r.status_code == 400


@pytest.mark.order(55)
@pytest.mark.unittest
def test_flowline_get_by_coords(f_client_testdb) -> None:
    coords = "POINT(-89.22401470690966 42.82769689708948)"
    r = f_client_testdb.get(f"{API_PREFIX}/linked-data/comid/position?f=json&coords={coords}")
    r.status_code == 200
    actual = r.json
    assert actual["features"][0]["id"] == 13297332


@pytest.mark.order(55)
@pytest.mark.unittest
def test_flowline_get_by_coords_bad_geom(f_client_testdb) -> None:
    coords = "PT(-89.22401470690966 42.82769689708948)"
    r = f_client_testdb.get(f"{API_PREFIX}/linked-data/comid/position?f=json&coords={coords}")
    r.status_code == 422
