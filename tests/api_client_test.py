#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import pytest

from nldi.server import APP


@pytest.mark.order(40)
@pytest.mark.unittest
def test_get_404():
    with APP.test_client() as client:
        response = client.get("/notfound")
    assert response.status_code == 404

@pytest.mark.order(40)
@pytest.mark.unittest
def test_get_root():
    with APP.test_client() as client:
        response = client.get("/api/nldi")
    assert response.status_code == 200
    assert response.headers["X-Powered-By"] == "nldi 0.1.0"
    assert response.headers["Content-Type"] == "application/json"

@pytest.mark.order(41)
@pytest.mark.unittest
def test_get_favicon():
    with APP.test_client() as client:
        response = client.get("/api/nldi/favicon.ico")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/vnd.microsoft.icon"

@pytest.mark.order(42)
@pytest.mark.unittest
def test_get_openapi():
    with APP.test_client() as client:
        response = client.get("/api/nldi/openapi?f=json")
    assert response.status_code == 200
    assert response.headers["Content-Type"] ==  "application/vnd.oai.openapi+json;version=3.0"


@pytest.mark.order(43)
@pytest.mark.unittest
def test_API_init():
    with APP.test_client() as client:
        response = client.get("/api/nldi/")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json["title"] is not None
    assert response.json["description"] is not None



@pytest.mark.order(44)
@pytest.mark.unittest
def test_API_linked_data():
    with APP.test_client() as client:
        response = client.get("/api/nldi/linked-data")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    source_list = response.json
    assert len(source_list) > 0
    assert source_list[0]["source"]  == "comid"


# POINT(-89.22401470690966 42.82769689708948)
@pytest.mark.order(44)
@pytest.mark.unittest
def test_API_feature_by_comid():
    with APP.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/13297166") # known good comid
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"

@pytest.mark.order(45)
@pytest.mark.unittest
def test_API_comid_by_position():
    with APP.test_client() as client:
        response = client.get("/api/nldi/linked-data/comid/position?coords=POINT(-89.22401470690966 42.82769689708948)")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json["type"] =="FeatureCollection"
    assert len(response.json["features"]) > 0
