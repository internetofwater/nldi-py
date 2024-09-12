#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""Test suite for nldi-py package"""

from copy import deepcopy

import pytest

from nldi.api import APIPlugin, FlowlinePlugin, CrawlerSourcePlugin


# region APIPlugin
@pytest.mark.order(40)
@pytest.mark.unittest
def test_baseplugin_constructor_smoketest():
    p = APIPlugin("test")
    assert p is not None
    assert p.name == "test"
    assert not p.is_registered
    assert p._db_connect_url is None


@pytest.mark.order(40)
@pytest.mark.unittest
def test_baseplugin_constructor_no_db():
    p = APIPlugin("test")
    assert p._db_connect_url is None
    with pytest.raises(RuntimeError):
        assert p.db_is_alive() is False


@pytest.mark.order(40)
@pytest.mark.integration
def test_baseplugin_constructor_with_db_connect_url(nldi_db_connect_string):
    p = APIPlugin("test", db_connect_url=nldi_db_connect_string)
    assert p is not None
    assert p.name == "test"
    assert not p.is_registered
    assert p.db_is_alive() is True  ## base APIPlugin class just attempts "SELECT 1", since it has no table model


@pytest.mark.order(40)
@pytest.mark.integration
def test_baseplugin_constructor_with_broken_db_connect_url(nldi_db_container):
    """All connection errors should return False; no exception raised!!!"""
    # wrong password
    _db_con_str = f"postgresql+psycopg2://{nldi_db_container['user']}:wrongpassword@{nldi_db_container['host']}:{nldi_db_container['port']}/{nldi_db_container['dbname']}"
    p = APIPlugin("test", db_connect_url=_db_con_str)
    assert p.db_is_alive() is False

    # wrong db name
    _db_con_str = f"postgresql+psycopg2://{nldi_db_container['user']}:{nldi_db_container['password']}@{nldi_db_container['host']}:{nldi_db_container['port']}/wrongdbname"
    p = APIPlugin("test", db_connect_url=_db_con_str)
    assert p.db_is_alive() is False


# region FlowlinePlugin
@pytest.mark.order(41)
@pytest.mark.integration
def test_flowlineplugin_constructor(nldi_db_connect_string):
    p = FlowlinePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    assert p.relative_url == ""  # << Unregistered flowline plugins should return empty string
    assert (
        p.db_is_alive() is True
    )  # << FlowlinePlugin has a table model, so it can check the connection by counting rows in the table.


@pytest.mark.order(41)
@pytest.mark.integration
def test_flowlineplugin_lookup(nldi_db_connect_string):
    p = FlowlinePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    flowline = p.get("13293396")  # << This COMID is known to be in the test database
    assert flowline["type"] == "Feature"
    assert str(flowline["properties"]["comid"]) == "13293396"
    assert flowline["geometry"]["type"] == "LineString"


@pytest.mark.order(41)
@pytest.mark.integration
def test_flowlineplugin_lookup_notfound(nldi_db_connect_string):
    p = FlowlinePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    with pytest.raises(KeyError):
        flowline = p.get("0000000")  # << this one is not in the test database


@pytest.mark.order(41)
@pytest.mark.integration
def test_flowlineplugin_lookup_badinput(nldi_db_connect_string):
    p = FlowlinePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    with pytest.raises(KeyError):
        flowline = p.get("this_is_not_an_int")  # << COMIDs have to be integers


# region CrawlerSourcePlugin
@pytest.mark.order(42)
@pytest.mark.integration
def test_crawlersource_plugin_constructor(nldi_db_connect_string):
    p = CrawlerSourcePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    assert p.db_is_alive() is True


@pytest.mark.order(42)
@pytest.mark.integration
def test_crawlersource_plugin_listall(nldi_db_connect_string):
    p = CrawlerSourcePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    src_list = p.get_all()
    assert len(src_list) > 0  # << There should be at least one source in the test database


@pytest.mark.order(42)
@pytest.mark.integration
def test_crawlersource_plugin_lookup_one_source(nldi_db_connect_string, mock_source):
    p = CrawlerSourcePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    sampled = p.get(mock_source["source_suffix"])

    for k in mock_source:
        if k == "source_suffix":
            assert sampled[k] == mock_source[k].lower()
            # The lookup function casts the source_id to lowercase for the search, and returns
            # the result with this modification.  We need to compare it as lowercase.
        else:
            assert sampled[k] == mock_source[k]


@pytest.mark.order(42)
@pytest.mark.integration
def test_crawlersource_plugin_lookup_one_source_notfound(nldi_db_connect_string):
    p = CrawlerSourcePlugin("FlowLine", db_connect_url=nldi_db_connect_string)
    with pytest.raises(KeyError):
        sampled = p.get("nosuchsource")


@pytest.mark.order(43)
@pytest.mark.integration
def test_crawersource_plugin_insert_new_source(nldi_db_connect_string):
    ## also tests delete_source
    p = CrawlerSourcePlugin("FlowLine", db_connect_url=nldi_db_connect_string)

    n = len(p.get_all())
    assert n == 3  # << There should be 3 sources in the test database
    dummy_src = {
        "crawler_source_id": 1000,
        "source_name": "Dummy Source Name",
        "source_suffix": "xxx",
        "source_uri": "https://www.example.com/data/feature",
        "feature_id": "DummyFeatureID",
        "feature_name": "DummyFeatureName",
        "feature_uri": "siteUrl",
        "feature_reach": None,
        "feature_measure": None,
        "ingest_type": "point",
        "feature_type": "varies",
    }
    success = p.insert_source(dummy_src)

    assert success is True
    assert len(p.get_all()) == n + 1

    ## delete the dummy entry we just inserted.
    p.delete_source(1000)
    assert len(p.get_all()) == n


@pytest.mark.order(43)
@pytest.mark.integration
def test_crawersource_plugin_update_existing_source(nldi_db_connect_string, mock_source):
    p = CrawlerSourcePlugin("FlowLine", db_connect_url=nldi_db_connect_string)

    n = len(p.get_all())
    assert n == 3  # << There should be 3 sources in the test database
    success = p.insert_source(mock_source)
    assert success is True
    assert len(p.get_all()) == n


@pytest.mark.order(43)
@pytest.mark.integration
def test_crawlersource_plugin_align_sources(nldi_db_connect_string, global_config):
    sources = global_config["sources"]
    p = CrawlerSourcePlugin("CrawlerSource", db_connect_url=nldi_db_connect_string)
    assert p.align_sources(sources, force=True) is True
    assert len(p.get_all()) == len(sources)
