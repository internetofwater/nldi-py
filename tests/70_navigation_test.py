#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#


"""
Various navigation services associated with a source.

Extends source-specific lookups, but focuses on the navigation business logic.

- [x] FeatureSourceModel Service -- nav methods
- [x] Navigation-specific endpoints:
  - [x] GET f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation"
  - [x] GET f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}"
  - [x] GET f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/flowlines"
  - [x] GET f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/{data_source}"

"""

import json

import httpx
import psycopg
import pytest

from nldi.db.schemas.nldi_data import CrawlerSourceModel, FeatureSourceModel
from nldi.domain.linked_data import repos, services

from . import API_PREFIX, AUTH_PREFIX

NAV_MODES = ["DM", "DD", "UT", "UM"]


# region Service
@pytest.mark.order(70)
@pytest.mark.integration
def test_repo_list_nav_modes(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    assert nav_svc is not None
    actual = nav_svc.modes
    assert isinstance(actual, list)
    assert len(actual) == 4
    for m in actual:
        assert m in NAV_MODES


@pytest.mark.order(70)
@pytest.mark.integration
async def test_svc_dm_from_comid(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    comid = 13294366
    q = nav_svc.dm(comid, 10.0)
    actual = await nav_svc.flowline_svc.list(statement=q)
    # produces a list of COMIDs matching the nav from the starting comid specified.
    expected = [13294366, 13293406, 13294268, 13293404, 13293396, 13293394, 13293398, 13294110]
    # expected according to https://nhgf.dev-wma.chs.usgs.gov/api/nldi/linked-data/comid/13294366/navigation/DM/flowlines?f=json&distance=10
    assert len(actual) == len(expected)


@pytest.mark.order(70)
@pytest.mark.integration
async def test_svc_dd_from_comid(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    comid = 13294366
    q = nav_svc.dd(comid, 10.0)
    actual = await nav_svc.flowline_svc.list(statement=q)
    expected = [13294366, 13293406, 13294268, 13293404, 13293400, 13293396, 13294110, 13293394, 13293398]
    # expected according to https://nhgf.dev-wma.chs.usgs.gov/api/nldi/linked-data/comid/13294366/navigation/DD/flowlines?f=json&distance=10
    assert isinstance(actual, list)
    assert len(actual) == len(expected)


@pytest.mark.order(70)
@pytest.mark.integration
async def test_svc_ut_from_comid(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    comid = 13294366
    q = nav_svc.ut(comid, 10.0)
    actual = await nav_svc.flowline_svc.list(statement=q)
    expected = [13294366]
    # expected according to https://nhgf.dev-wma.chs.usgs.gov/api/nldi/linked-data/comid/13294366/navigation/UT/flowlines?f=json&distance=10
    assert isinstance(actual, list)
    assert len(actual) == len(expected)


@pytest.mark.order(70)
@pytest.mark.integration
async def test_svc_um_from_comid(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    comid = 13294366
    q = nav_svc.um(comid, 10.0)
    actual = await nav_svc.flowline_svc.list(statement=q)
    expected = [13294366]
    # expected according to https://nhgf.dev-wma.chs.usgs.gov/api/nldi/linked-data/comid/13294366/navigation/UM/flowlines?f=json&distance=10
    assert isinstance(actual, list)
    assert len(actual) == len(expected)


@pytest.mark.order(70)
@pytest.mark.integration
async def test_svc_estimate_measure(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    source_name = "wqp"
    identifier = "USGS-05427930"
    actual = await nav_svc.estimate_measure(identifier, source_name)
    assert actual == pytest.approx(16.633304437714568)


@pytest.mark.order(71)
@pytest.mark.integration
async def test_svc_nav_wrapper_function(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    comid = 13294366

    a = await nav_svc.flowline_svc.list(statement=nav_svc.um(comid, 10.0))
    b = await nav_svc.flowline_svc.list(statement=nav_svc.navigation("UM", comid, 10.0))
    assert a == b

    a = await nav_svc.flowline_svc.list(statement=nav_svc.ut(comid, 10.0))
    b = await nav_svc.flowline_svc.list(statement=nav_svc.navigation("UT", comid, 10.0))
    assert a == b

    a = await nav_svc.flowline_svc.list(statement=nav_svc.dm(comid, 10.0))
    b = await nav_svc.flowline_svc.list(statement=nav_svc.navigation("DM", comid, 10.0))
    assert a == b

    a = await nav_svc.flowline_svc.list(statement=nav_svc.dd(comid, 10.0))
    b = await nav_svc.flowline_svc.list(statement=nav_svc.navigation("DD", comid, 10.0))
    assert a == b


@pytest.mark.order(72)
@pytest.mark.integration
async def test_svc_dm_from_comid_as_features(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    comid = 13294366
    ## Construct the query by hand....
    q = nav_svc.dm(comid, 10.0)
    actual_direct = await nav_svc.flowline_svc.features_from_nav_query(q)

    ## Use the wrapper in the service/business-logic layer
    actual_from_bl = await nav_svc.walk_flowlines("comid", comid, "DM", 10.0)
    assert len(actual_direct) == len(actual_from_bl)


@pytest.mark.order(73)
@pytest.mark.integration
async def test_svc_dm_from_comid_trimmed(dbsession_containerized) -> None:
    nav_svc = services.NavigationService(session=dbsession_containerized)
    source_name = "wqp"
    identifier = "USGS-05427930"
    actual = await nav_svc.walk_flowlines(source_name, identifier, "UT", 10.0, True)
    assert len(actual) == 5
    # https://nhgf.dev-wma.chs.usgs.gov/api/nldi/linked-data/wqp/USGS-05427930/navigation/UT/flowlines?f=json&distance=10&trimStart=true


# region Litestar Endpoints
@pytest.mark.order(75)
@pytest.mark.integration
def test_api_get_nav_modes_by_id(client_containerized) -> None:
    source_name = "wqp"
    identifier = "USGS-05427930"

    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation?f=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    actual = r.json()
    for expected_key in ["upstreamMain", "upstreamTributaries", "downstreamMain", "downstreamDiversions"]:
        assert expected_key in actual
        assert actual[expected_key] != ""


@pytest.mark.order(75)
@pytest.mark.parametrize("nav_mode", NAV_MODES)
@pytest.mark.integration
def test_api_get_each_nav_mode_by_id(client_containerized, nav_mode) -> None:
    source_name = "wqp"
    identifier = "USGS-05427930"

    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}?f=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    actual = r.json()
    assert isinstance(actual, list)
    actual_comid = actual[0]  # should always be first
    assert actual_comid["source"] == "Flowlines"
    assert actual_comid["features"].endswith(f"{nav_mode}/flowlines")
    assert len(actual) > 1


@pytest.mark.order(75)
@pytest.mark.integration
def test_api_get_navigated_flowlines(client_containerized) -> None:
    source_name = "wqp"
    identifier = "USGS-05427930"

    # https://nhgf.dev-wma.chs.usgs.gov/api/nldi/linked-data/wqp/USGS-05427930/navigation/UT/flowlines?f=json&distance=10
    r = client_containerized.get(
        f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/UT/flowlines?f=json&distance=10"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    actual = r.json()
    assert actual["type"] == "FeatureCollection"
    assert isinstance(actual["features"], list)
    assert len(actual["features"]) == 5


@pytest.mark.order(75)
@pytest.mark.integration
def test_api_get_navigated_flowlines_trimmed(client_containerized) -> None:
    source_name = "wqp"
    identifier = "USGS-05427930"

    # https://nhgf.dev-wma.chs.usgs.gov/api/nldi/linked-data/wqp/USGS-05427930/navigation/UT/flowlines?f=json&distance=10&trimStart=true
    r = client_containerized.get(
        f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/UT/flowlines?f=json&distance=10&trimStart=true"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    actual = r.json()
    assert actual["type"] == "FeatureCollection"
    assert isinstance(actual["features"], list)
    assert len(actual["features"]) == 5


@pytest.mark.order(75)
@pytest.mark.integration
def test_api_get_each_nav_mode_by_id_othersource(client_containerized) -> None:
    source_name = "wqp"
    identifier = "USGS-05427930"
    second_source = "nwissite"

    nav_mode = "UT"

    r = client_containerized.get(
        f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/{second_source}?f=json&distance=10.0"
    )
    assert r.status_code == 200


# region parity tests
@pytest.mark.order(78)
@pytest.mark.system
@pytest.mark.parametrize("nav_mode", NAV_MODES)
def test_api_get_navigated_flowlines_trimmed_system(client_testdb, nav_mode) -> None:
    source_name = "wqp"
    identifier = "USGS-05427930"

    r = httpx.get(
        f"{AUTH_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/flowlines?f=json&distance=10&trimStart=true",
        verify=False,
    )
    expected = r.json()

    r = client_testdb.get(
        f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/flowlines?f=json&distance=10&trimStart=true",
    )
    actual = r.json()

    assert actual["type"] == expected["type"]
    # Same flowlines returned (check by comid)
    assert len(actual["features"]) == len(expected["features"])
    expected_comids = [int(f["properties"]["nhdplus_comid"]) for f in expected["features"]]
    actual_comids = [int(f["properties"]["nhdplus_comid"]) for f in actual["features"]]
    for c in expected_comids:
        assert c in actual_comids

    # same properties?
    assert len(expected['features'][0]['properties']) == len(actual['features'][0]['properties'])
    for k in expected['features'][0]['properties']:
        assert k in actual['features'][0]['properties']



@pytest.mark.order(78)
@pytest.mark.system
@pytest.mark.parametrize("nav_mode", NAV_MODES)
def test_api_get_navigated_features_trimmed_system(client_testdb, nav_mode) -> None:
    source_name = "wqp"
    identifier = "USGS-05427930"

    r = httpx.get(
        f"{AUTH_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/nwissite?f=json&distance=10",
        verify=False,
    )
    expected = r.json()

    r = client_testdb.get(
        f"{API_PREFIX}/linked-data/{source_name}/{identifier}/navigation/{nav_mode}/nwissite?f=json&distance=10"
    )
    actual = r.json()

    assert actual["type"] == expected["type"]
    assert len(actual["features"]) == len(expected["features"])

