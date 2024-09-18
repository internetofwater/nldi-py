#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
Test suite for nldi-py package

Here is where we test
"""

from copy import deepcopy

import pytest

from nldi.api import API
from nldi.api.plugins import *

from nldi.server import APP


@pytest.mark.order(50)
@pytest.mark.unittest
def test_new_API_smoke(global_config):
    api = API(globalconfig=global_config)
    assert api is not None
    assert str(api.db_connection_string).startswith("postgresql+psycopg2://nldi:changeMe@")


@pytest.mark.order(51)
@pytest.mark.integration
def test_new_API_w_sources(global_config):
    api = API(globalconfig=global_config)
    assert api.sources.db_is_alive()


@pytest.mark.order(51)
@pytest.mark.integration
def test_register_APIPlugin_failure(global_config):
    dummy_config = deepcopy(global_config)
    dummy_config["server"]["data"]["port"] = 1  # Known bad port
    api = API(globalconfig=dummy_config)
    p = APIPlugin("test")
    success = api.register_plugin(p)
    assert not success


@pytest.mark.order(51)
@pytest.mark.unittest
def test_register_APIPlugin_success(global_config):
    api = API(globalconfig=global_config)
    p = APIPlugin("test")
    success = api.register_plugin(p)
    assert success
    assert len(api.plugins) == 1

