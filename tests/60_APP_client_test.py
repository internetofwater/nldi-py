#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
Test suite for nldi-py package

This test suite is for the API endpoints, to see if they map to the correct business logic and produce
reasonable results.  Business logic for each endpoint is tested separately in the various plugins tests.
"""

import pytest

from nldi.server import app_factory
from nldi.api import API


@pytest.mark.order(44)
@pytest.mark.unittest
def test_API_linked_data(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    source_list = response.json
    assert len(source_list) > 0
    assert source_list[0]["source"] == "comid"


@pytest.mark.order(44)
@pytest.mark.unittest
def test_API_feature_by_comid(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/13297166")  # known good comid
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"


@pytest.mark.order(45)
@pytest.mark.unittest
def test_API_comid_by_position(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/position?coords=POINT(-89.22401470690966 42.82769689708948)")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json["type"] == "FeatureCollection"
    assert len(response.json["features"]) > 0
