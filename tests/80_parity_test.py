#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#
"""
Test against current NLDI "production" database.

These tests connect to a real copy of the current production database (rather than to a
containerized extract of the database )

Routes to test:
* /api/nldi/linked-data                                  # list of all sources
* /api/nldi/linked-data/{src}/{id}                       # where we test src=comid and one other src (e.g. wqp)
* /api/nldi/linked-data/{src}/{id}/basin                 # where we test src=comid and one other src (e.g. wqp)
* /api/nldi/linked-data/{src}/{id}/navigation            # where we test src=comid and one other src (e.g. wqp)
* /api/nldi/linked-data/{src}/{id}/navigation/{mode}/{src2} # where we test src=comid and one other src (e.g. wqp)
* /api/nldi/linked-data/comid/position?coords=POINT(X Y)
* /api/nldi/linked-data/hydrolocation?coords=POINT(X Y)

"""

import logging
import os

import httpx
import pytest
import sqlalchemy

from nldi import util
from nldi.api import API
from nldi.server import app_factory


# region smoke-tests
@pytest.mark.order(80)
@pytest.mark.parity
def test_database_connection_smoketest(prod_db_connect_string):
    """Test that we can connect to the database."""
    logging.info(f"Connecting to {prod_db_connect_string!r}")
    engine = sqlalchemy.create_engine(prod_db_connect_string)
    with engine.begin() as connection:
        (v,) = connection.execute(sqlalchemy.text("SELECT 1")).fetchone()
    assert v == 1


@pytest.mark.order(10)
@pytest.mark.unittest
def test_read_yaml_file(config_yaml, prod_env_update):
    """Standard usage: read a YAML file into a dict, if given a pathlib.Path object."""
    os.environ.update(prod_env_update)
    cfg = util.load_yaml(config_yaml)
    sources = cfg["sources"]
    assert len(sources) == 3
    suffixes = [src["source_suffix"] for src in sources]
    assert "WQP" in suffixes
    assert "nwissite" in suffixes
    assert "huc12pp" in suffixes
    assert cfg["server"]["data"]["host"] == "nldi-db-development.dev-nwis.usgs.gov"


# region /api/nldi/linked-data
@pytest.mark.order(80)
@pytest.mark.parity
def test_API_linked_data(prod_global_config):
    """
    Get the list of sources

    Tests route "/api/nldi/linked-data"
    """
    _api = API(globalconfig=prod_global_config)
    _app = app_factory(_api)

    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    test_sources_list = [s["source"] for s in response.json]

    # production:
    prod_response = httpx.get("https://labs.waterdata.usgs.gov/api/nldi/linked-data?f=json")
    prod_sources_list = [s["source"] for s in prod_response.json()]

    assert len(test_sources_list) == len(prod_sources_list)
    for src in prod_sources_list:
        assert src in test_sources_list


# region /api/nldi/linked-data/{src}/{id}
@pytest.mark.order(60)
@pytest.mark.integration
def test_API_feature_by_comid(prod_global_config):
    """
    FlowLine Plugin Test

    Tests Route: "/api/nldi/linked-data/comid/{comid}" with a known good comid: 13297166
    """
    _api = API(globalconfig=prod_global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/13297166")  # known good comid
    test_feature = response.json["features"][0]

    # production:
    prod_response = httpx.get("https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/comid/13297166")
    prod_feature = prod_response.json()["features"][0]

    # geometry
    assert test_feature["geometry"]["type"] == prod_feature["geometry"]["type"]
    assert test_feature["geometry"]["coordinates"] == prod_feature["geometry"]["coordinates"]

    # properties
    for k, f in prod_feature["properties"].items():
        if k == "navigation":  # navigation will be different due to different base-url
            continue
        assert test_feature["properties"][k] == f


@pytest.mark.order(60)
@pytest.mark.integration
def test_API_lookup_feature_by_comid(prod_global_config):
    """
    FlowLine Plugin Test

    Tests Route: "/api/nldi/linked-data/comid/{comid}" with a known good comid: 13297166
    """
    _api = API(globalconfig=prod_global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/13297166")  # known good comid
    test_feature = response.json["features"][0]

    # production:
    prod_response = httpx.get("https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/comid/13297166")
    prod_feature = prod_response.json()["features"][0]

    # geometry
    assert test_feature["geometry"]["type"] == prod_feature["geometry"]["type"]
    assert test_feature["geometry"]["coordinates"] == prod_feature["geometry"]["coordinates"]

    # properties
    for k, f in prod_feature["properties"].items():
        if k == "navigation":  # navigation will be different due to different base-url
            continue
        assert test_feature["properties"][k] == f


@pytest.mark.order(81)
@pytest.mark.unittest
def test_lookup_feature_by_src_and_id(prod_global_config):
    _api = API(globalconfig=prod_global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        test_response = client.get("/api/nldi/linked-data/wqp/WIDNR_WQX-133338")
    assert test_response.status_code == 200
    test_feature = test_response.json["features"][0]

    #
    prod_response = httpx.get("https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/wqp/WIDNR_WQX-133338?f=json")
    prod_feature = prod_response.json()["features"][0]

    # geometry
    assert test_feature["geometry"]["type"] == prod_feature["geometry"]["type"]
    assert test_feature["geometry"]["coordinates"] == prod_feature["geometry"]["coordinates"]

    # properties
    for k, f in prod_feature["properties"].items():
        if k == "navigation":
            continue
        assert test_feature["properties"][k] == f


# Routes to test:
# /api/nldi/linked-data (list of all sources)
# /api/nldi/linked-data/{source}/{identifier}  # where we test source=comid and one other source (e.g. wqp)
# /api/nldi/linked-data/{source}/{identifier}/basin # where we test source=comid and one other source (e.g. wqp)
# /api/nldi/linked-data/{source}/{identifier}/navigation # where we test source=comid and one other source (e.g. wqp)
# /api/nldi/linked-data/{source}/{identifier}/navigation/{mode}/{src2} # where we test source=comid and one other source (e.g. wqp)
# /api/nldi/linked-data/comid/position?coords=POINT(X Y)
# /api/nldi/linked-data/hydrolocation?coords=POINT(X Y)


# region /api/nldi/linked-data/{src}/{id}/basin
@pytest.mark.order(81)
@pytest.mark.unittest
def test_source_linked_data_basin(prod_global_config):
    # @ROOT.route("/linked-data/<path:source_name>/<path:identifier>/basin")
    _api = API(globalconfig=prod_global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        test_response = client.get("/api/nldi/linked-data/WQP/USGS-05427930/basin")
        assert test_response.status_code == 200

    # NOTE: the current production service does not propperly lower-case the source name.  must use all upper-case
    prod_response = httpx.get("https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/WQP/USGS-05427930/basin?f=json")
    assert prod_response.status_code == 200
    # we should get a FeatureCollection with exactly one feature in it (the basin) and no properties.
    assert len(test_response.json["features"]) == 1
    assert len(prod_response.json()["features"]) == 1
    assert (
        test_response.json["features"][0]["geometry"]["type"] == prod_response.json()["features"][0]["geometry"]["type"]
    )
    ## TODO compare coordinates? or just assume that the geometry is correct?  Maybe compute the area of the polygons and compare that?


# region /api/nldi/linked-data/{src}/{id}/navigation
@pytest.mark.order(81)
@pytest.mark.unittest
def test_source_linked_data_navigation(prod_global_config):
    _api = API(globalconfig=prod_global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        test_response = client.get("/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM")
    assert test_response.status_code == 200

    prod_response = httpx.get(
        "https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/wqp/USGS-05427930/navigation/UM?f=json"
    )

    assert len(test_response.json) == len(prod_response.json())


# @pytest.mark.order(81)
# @pytest.mark.unittest
# def test_lookup_feature_by_src_and_id(prod_global_config):
#     _api = API(globalconfig=prod_global_config)
#     _app = app_factory(_api)
#     with _app.test_client() as client:
#         # response = client.get("/api/nldi/linked-data/wqp/USGS-05427930")
#         test_response = client.get("/api/nldi/linked-data/wqp/WIDNR_WQX-133338")
#     assert test_response.status_code == 200

#     #
#     prod_response = httpx.get("https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/wqp/WIDNR_WQX-133338?f=json")
