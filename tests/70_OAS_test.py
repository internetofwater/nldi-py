#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""Test suite for nldi-py package"""

from copy import deepcopy

import pytest

from nldi.api import API, APIPlugin, FlowlinePlugin
from nldi.server import APP


@pytest.mark.order(40)
@pytest.mark.unittest
def test_get_404():
    with APP.test_client() as client:
        response = client.get("/notfound")
    assert response.status_code == 404
