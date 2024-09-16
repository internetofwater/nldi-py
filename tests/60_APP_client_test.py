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


@pytest.mark.order(60)
@pytest.mark.integration
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


@pytest.mark.order(60)
@pytest.mark.integration
def test_API_feature_by_comid(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/13297166")  # known good comid
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"


@pytest.mark.order(60)
@pytest.mark.integration
def test_API_comid_by_position(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/position?coords=POINT(-89.22401470690966 42.82769689708948)")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json["type"] == "FeatureCollection"
    assert len(response.json["features"]) > 0


@pytest.mark.order(60)
@pytest.mark.integration
def test_API_hydrolocation(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/hydrolocation?coords=POINT(-89.22401470690966 42.82769689708948)")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json["type"] == "FeatureCollection"
    assert len(response.json["features"]) == 2
    assert response.json["features"][0]["properties"]["source"] == "indexed"
    assert response.json["features"][1]["properties"]["source"] == "provided"
    assert str(response.json["features"][0]["properties"]["comid"]) == "13297332"  #<< known good comid
    #      ^^^^^^^^^^^ "correct" responses obtained from
    #      https://labs.waterdata.usgs.gov/api/nldi/linked-data/hydrolocation?f=json&coords=POINT(-89.22401470690966%2042.82769689708948)


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data(global_config):
    # @ROOT.route("/linked-data/<path:source_name>")
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>")
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp")
        assert response.status_code == 200

        response = client.get("/api/nldi/linked-data/wqp/1234")
        assert response.status_code == 200


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_basin(global_config):
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/basin")
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/1234/basin")
        assert response.status_code == 200


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_navigation(global_config):
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation")  # noqa
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>")  # noqa
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/navigation")
        assert response.status_code == 200

        response = client.get("/api/nldi/linked-data/wqp/navigation/mode")
        assert response.status_code == 200



@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_flowlines(global_config):
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/flowlines")  # noqa
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/navigation/mode/flowlines")
        assert response.status_code == 200


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_source(global_config):
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/<path:data_source>")  # noqa
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/navigation/mode/src")
        assert response.status_code == 200
