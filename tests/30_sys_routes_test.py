#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
Accessing routes/endpoints (rather than business logic functions).

We just want to test that a given endpoint/route invokes the correct function/handler. The
tests of those handlers will be handled elsewhere.
"""

import logging

import pytest
from litestar.testing import TestClient

from . import API_PREFIX


# region localhost
@pytest.mark.order(20)
@pytest.mark.unittest
def test_core_system_routes(client_localhost) -> None:
    """
    Fetch infrastructure files/routes; not relevant to API function itself.

      * robots.txt
      * faviocon.ico
    """
    r = client_localhost.get(f"{API_PREFIX}/robots.txt")
    assert r.status_code == 200

    r = client_localhost.get(f"{API_PREFIX}/favicon.ico")
    assert r.status_code == 200


@pytest.mark.order(21)
@pytest.mark.unittest
def test_server_config_form(client_localhost) -> None:
    """We're not checking for valid data -- just that the path returns JSON of the right form."""
    r = client_localhost.get(f"{API_PREFIX}/about/config")
    assert r.status_code == 200
    actual = r.json()
    assert actual["server"].get("url")
    assert actual["server"].get("prefix")

    assert actual["db"].get("host")
    assert actual["db"].get("port")


@pytest.mark.order(21)
@pytest.mark.unittest
def test_server_healthcheck_form(client_localhost) -> None:
    """
    Health endpoint returns a list of status objects (one for each dependent subsystem).

    We don't care about the actual status (at this point) -- just that we get the right object/structure.
    """
    r = client_localhost.get(f"{API_PREFIX}/about/health")
    assert r.status_code == 200
    actual = r.json()
    assert isinstance(actual, dict)
    assert actual.get("server") is not None
    assert actual.get("db") is not None
    assert actual.get("pygeoapi") is not None


@pytest.mark.order(21)
@pytest.mark.unittest
def test_server_health_db(client_localhost) -> None:
    r = client_localhost.get(f"{API_PREFIX}/about/health/db")
    assert r.status_code == 200
    actual = r.json()
    assert isinstance(actual, dict)
    assert actual.get("cfg").startswith("postgresql")


@pytest.mark.order(21)
@pytest.mark.unittest
def test_server_health_pygeoapi(client_localhost) -> None:
    r = client_localhost.get(f"{API_PREFIX}/about/health/pygeoapi")
    assert r.status_code == 200
    actual = r.json()
    assert isinstance(actual, dict)
    assert actual.get("cfg").startswith("http")


# region containerized
## Here, we're checking that config matches expected values and that we have function to the database
@pytest.mark.order(22)
@pytest.mark.unittest
def test_server_db_config_container(client_containerized) -> None:
    r = client_containerized.get(f"{API_PREFIX}/about/config")
    assert r.status_code == 200
    actual = r.json()
    assert actual["db"].get("host").startswith("172.")  # <<< WARNING -- this may not be true on all systems.

    r = client_containerized.get(f"{API_PREFIX}/about/health/db")
    assert r.status_code == 200
    actual = r.json()
    assert actual["status"] == "online"


# region testdb
# Testing aginst the in-the-cloud test database
@pytest.mark.order(22)
@pytest.mark.integration
def test_server_db_config_testdb(client_testdb) -> None:
    r = client_testdb.get(f"{API_PREFIX}/about/config")
    assert r.status_code == 200
    actual = r.json()
    assert actual["db"].get("host") == "nldi-db-development.dev-nwis.usgs.gov"  # < Magic value

    r = client_testdb.get(f"{API_PREFIX}/about/health/db")
    assert r.status_code == 200
    actual = r.json()
    assert actual["status"] == "online" #< will only pass if the db really is online.
