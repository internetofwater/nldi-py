#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
Test suite for nldi-py API Endpoints.

These tests should execute, with or without a database connection.  They just test the core APP
endpoints, not those served by the database.
"""

from copy import deepcopy

import pytest

from nldi import __version__
from nldi.api import API
from nldi.api.plugins import *
from nldi.server import APP, app_factory


@pytest.mark.order(70)
@pytest.mark.unittest
def test_get_root():
    with APP.test_client() as client:
        response = client.get("/api/nldi")
    assert response.status_code == 200
    assert response.headers["X-Powered-By"] == f"nldi {__version__}"
    assert response.headers["Content-Type"] == "application/json"


@pytest.mark.order(70)
@pytest.mark.unittest
def test_get_404():
    with APP.test_client() as client:
        response = client.get("/notfound")
    assert response.status_code == 404


@pytest.mark.order(70)
@pytest.mark.unittest
def test_get_favicon():
    with APP.test_client() as client:
        response = client.get("/api/nldi/favicon.ico")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/vnd.microsoft.icon"


@pytest.mark.order(70)
@pytest.mark.unittest
def test_get_openapi():
    with APP.test_client() as client:
        response = client.get("/api/nldi/openapi?f=json")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/vnd.oai.openapi+json;version=3.0"


@pytest.mark.order(70)
@pytest.mark.unittest
def test_get_about_stuff(global_config):

    ## NOTE: the healthcheck endpoint pings the database, so we need to get a valid config:
    _api = API(globalconfig=global_config)
    _app = app_factory(_api)
    with _app.test_client() as client:
        response = client.get("/api/nldi/about/info")
        assert response.status_code == 200
        response = client.get("/api/nldi/about/health")
        assert response.status_code == 200
