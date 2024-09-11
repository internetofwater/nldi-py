#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""Test suite for nldi-py package"""

from copy import deepcopy

import pytest

from nldi.api import API, APIPlugin, FlowlinePlugin


@pytest.mark.order(40)
@pytest.mark.unittest
def test_new_API_smoke(global_config):
    api = API(globalconfig=global_config)
    assert api is not None
    assert str(api.db_connection_string).startswith("postgresql+psycopg2://nldi:changeMe@")


@pytest.mark.order(40)
@pytest.mark.unittest
def test_new_API_w_sources(global_config):
    api = API(globalconfig=global_config)
    assert api.sources.db_is_alive()


@pytest.mark.order(40)
@pytest.mark.unittest
def test_register_APIPlugin_failure(global_config):
    dummy_config = deepcopy(global_config)
    dummy_config["server"]["data"]["port"] = 1  # Known bad port
    api = API(globalconfig=dummy_config)
    p = APIPlugin("test")
    success = api.register_plugin(p)
    assert not success


@pytest.mark.order(40)
@pytest.mark.unittest
def test_register_APIPlugin_success(global_config):
    api = API(globalconfig=global_config)
    p = APIPlugin("test")
    success = api.register_plugin(p)
    assert success
    assert len(api.plugins) == 1


@pytest.mark.order(40)
@pytest.mark.unittest
def test_register_FlowlinePlugin(global_config):
    api = API(globalconfig=global_config)
    p = FlowlinePlugin("FlowLine")
    success = api.register_plugin(p)
    assert success
    assert len(api.plugins) == 1
    with pytest.raises(KeyError):
        f = api.plugins["FlowLine"].get("12345678")
    f = api.plugins["FlowLine"].get("13293396")
    assert f["geometry"] is not None
    # assert f["properties"]["mainstem"] ## TODO: find a COMID with a mainstem relationship


@pytest.mark.order(41)
@pytest.mark.unittest
def test_crawlersource_plugin_get_all_sources(global_config):
    api = API(globalconfig=global_config)
    n = api.sources.get_all()
    assert len(n) > 0


@pytest.mark.order(41)
@pytest.mark.unittest
def test_crawlersource_plugin_lookup_one_source(global_config, mock_source):
    api = API(globalconfig=global_config)
    s = api.sources.get(mock_source["source_suffix"])
    for k in mock_source:
        if k == "source_suffix":
            assert s[k] == mock_source[k].lower()
            # The lookup function casts the source_id to lowercase for the search, and returns
            # the result with this modification.  We need to compare it as lowercase.
        else:
            assert s[k] == mock_source[k]


@pytest.mark.order(41)
@pytest.mark.unittest
def test_crawlersource_plugin_lookup_one_source_notfound(global_config):
    api = API(globalconfig=global_config)
    with pytest.raises(KeyError):
        s = api.sources.get("nosuchsource")
