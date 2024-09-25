#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
Test suite for nldi-py package

This test suite is for the API endpoints, to see if they map to the correct business logic and produce
reasonable results.  Busines s logic for each endpoint is tested separately in the various plugins tests.
"""

import pytest

from nldi.api import API
from nldi.server import app_factory


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
    assert len(source_list) >= 4
    assert source_list[0]["source"] == "comid"
    for src in source_list:
        assert src["source"].lower() in [
            "comid",
            "wqp",
            "nwissite",
            "huc12pp",
        ]  # these are the sources we know about in the test db.


@pytest.mark.order(60)
@pytest.mark.integration
def test_API_feature_by_comid(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/13297166")  # known good comid
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    # compare result with current "production" response from https://labs.waterdata.usgs.gov/api/nldi/linked-data/comid/13297166

    assert response.json["type"] == "FeatureCollection"
    f = response.json["features"][0]
    assert f["properties"]["source"] == "comid"
    assert int(f["properties"]["identifier"]) == 13297166
    assert f["properties"]["navigation"].endswith("/linked-data/comid/13297166/navigation")


@pytest.mark.order(60)
@pytest.mark.integration
def test_API_comid_by_position(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/position?coords=POINT(-89.509 43.087)")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json["type"] == "FeatureCollection"
    assert len(response.json["features"]) > 0
    ## compare result with current "production" response from https://labs.waterdata.usgs.gov/api/nldi/linked-data/comid/position?f=json&coords=POINT%28-89.509%2043.087%29
    f = response.json["features"][0]
    assert f["properties"]["source"] == "comid"
    assert int(f["properties"]["comid"]) == 13294314
    assert f["properties"]["navigation"].endswith("/linked-data/comid/13294314/navigation")


@pytest.mark.order(60)
@pytest.mark.integration
def test_API_hydrolocation(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/hydrolocation?coords=POINT(-89.509 43.087)")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json["type"] == "FeatureCollection"
    assert len(response.json["features"]) == 2
    assert response.json["features"][0]["properties"]["source"] == "indexed"
    assert response.json["features"][1]["properties"]["source"] == "provided"
    # compare result with current "production" response from https://labs.waterdata.usgs.gov/api/nldi/linked-data/hydrolocation?f=json&coords=POINT%28-89.509%2043.087%29
    f = response.json["features"][0]
    assert str(f["properties"]["comid"]) == "13294314"
    assert f["properties"]["measure"] == pytest.approx(82.860346, 1e-06)
    assert f["properties"]["navigation"].endswith("/linked-data/comid/13294314/navigation")
    assert f["properties"]["reachcode"] == "07090002008384"
    assert f["geometry"]["type"] == "Point"


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_one_feature(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        # response = client.get("/api/nldi/linked-data/wqp/USGS-05427930")
        response = client.get("/api/nldi/linked-data/wqp/WIDNR_WQX-133338")

        assert response.status_code == 200
    # compare result with current "production" response from https://labs.waterdata.usgs.gov/api/nldi/linked-data/wqp/WIDNR_WQX-133338
    assert response.json["type"] == "FeatureCollection"
    assert len(response.json["features"]) == 1
    f = response.json["features"][0]
    assert f["properties"]["source"].lower() == "wqp"
    assert f["properties"]["identifier"] == "WIDNR_WQX-133338"
    assert f["properties"]["navigation"].endswith("/linked-data/wqp/WIDNR_WQX-133338/navigation")
    assert f["properties"]["name"] == "Curb at Gately and Tokay Blvd"
    assert str(f["properties"]["comid"]) == "13294376"
    assert f["geometry"]["type"] == "Point"


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_all_features(global_config):
    # @ROOT.route("/linked-data/<path:source_name>")
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp")
        assert response.status_code == 200
        assert len(response.json["features"]) > 1100  ## wqp has 1100+ features


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_basin(global_config):
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/basin")
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/basin")
        assert response.status_code == 200
    ##NOTE: I was unable to get any basin response to work from labs.waterdata.usgs.gov, so I can't compare the result.


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_navigation(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation")
        assert response.status_code == 200
        # compare response with https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/wqp/USGS-05427930/navigation?f=json
        d = response.json
        assert len(d) == 4  # 4 keys: upstreamMain, upstreamTributaries, downstreamMain, downstreamDiversions
        for k in d:
            assert k in ["upstreamMain", "upstreamTributaries", "downstreamMain", "downstreamDiversions"]

        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM")
        assert response.status_code == 200
        # compare response with https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM?f=json
        # NOTE: the production database has many more sources than our test database, so the result will be different.
        assert len(response.json) >= 4  # 4 is minimum for our test database (3 sources plus 'flowlines')
        for _item in response.json:
            assert _item["source"] is not None
            assert _item["features"] is not None
            assert _item["sourceName"] is not None


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_flowlines(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM/flowlines?distance=10")
        assert response.status_code == 200

        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM/flowlines")
        assert response.status_code == 400  ## distance param requried

        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM/flowlines?distance=abc")
        assert response.status_code == 400  ## distance param must be a number


@pytest.mark.order(61)
@pytest.mark.unittest
def test_source_linked_data_source(global_config):
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/navigation/<path:nav_mode>/<path:data_source>")  # noqa
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/mode/src?distance=10")
        assert response.status_code == 400  # invalid mode "mode"

        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM/src?distance=10")
        assert response.status_code == 400


@pytest.mark.order(65)
@pytest.mark.integration
def test_nav_list_all_modes(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation")
        assert response.status_code == 200
    assert len(response.json) == 4
    for k in response.json:
        assert k in ["upstreamMain", "upstreamTributaries", "downstreamMain", "downstreamDiversions"]
    assert response.json["upstreamMain"].endswith("UM")
    assert response.json["upstreamTributaries"].endswith("UT")
    assert response.json["downstreamMain"].endswith("DM")
    assert response.json["downstreamDiversions"].endswith("DD")


@pytest.mark.order(65)
@pytest.mark.integration
def test_nav_UM_mode(global_config):
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM")
        assert response.status_code == 200
    assert len(response.json) >= 4  # 4 is minimum for our test database (3 sources plus 'flowlines')
    assert response.json[0]["source"] == "Flowlines"
