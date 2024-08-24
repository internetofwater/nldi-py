#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""Test suite for nldi-py package"""

import pytest

from nldi.api import API, APIPlugin


@pytest.mark.order(40)
@pytest.mark.unittest
def test_new_API_smoke(dummy_db_config):
    api = API(db_info=dummy_db_config)
    assert api is not None
    assert str(api.db_connection_string) == "postgresql+psycopg2://nldi:changeMe@localhost:5432/nldi"

@pytest.mark.order(40)
@pytest.mark.unittest
def test_new_API_w_sources(nldi_db_container):
    api = API(db_info=nldi_db_container)
    assert api.sources.db_is_alive()

@pytest.mark.order(40)
@pytest.mark.unittest
def test_register_APIPlugin_failure(dummy_db_config):
    dummy_db_config["port"] = 1  # Known bad port
    api = API(db_info=dummy_db_config)
    p = APIPlugin("test")
    success = api.register_plugin(p)
    assert not success


@pytest.mark.order(40)
@pytest.mark.unittest
def test_register_APIPlugin_success(nldi_db_container):
    api = API(db_info=nldi_db_container)
    p = APIPlugin("test")
    success = api.register_plugin(p)
    assert success
    assert len(api.get_plugins()) == 1


@pytest.mark.order(41)
@pytest.mark.unittest
def test_crawlersource_plugin_get_all_sources(nldi_db_container):
    api = API(db_info=nldi_db_container)
    n = api.sources.get_all()
    assert len(n) > 0


@pytest.mark.order(41)
@pytest.mark.unittest
def test_crawlersource_plugin_lookup_one_source(nldi_db_container, mock_source):
    api = API(db_info=nldi_db_container)
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
def test_crawlersource_plugin_lookup_one_source_notfound(nldi_db_container):
    api = API(db_info=nldi_db_container)
    with pytest.raises(KeyError):
        s = api.sources.get("nosuchsource")
