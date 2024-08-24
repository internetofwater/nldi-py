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
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Powered-By"] == "nldi 0.1.0"
    assert response.headers["Content-Type"] == "application/json"

@pytest.mark.order(41)
@pytest.mark.unittest
def test_get_favicon():
    with APP.test_client() as client:
        response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/vnd.microsoft.icon"

# @pytest.mark.order(42)
# @pytest.mark.unittest
# def test_get_openapi():
#     with APP.test_client() as client:
#         response = client.get("/openapi")
#     assert response.status_code == 200
#     assert response.headers["Content-Type"] == "application/json"


# @pytest.mark.order(43)
# @pytest.mark.unittest
# def test_API_init():
#     with APP.test_client() as client:
#         response = client.get("/api")
#     assert response.status_code == 200
#     assert response.headers["Content-Type"] == "application/json"

