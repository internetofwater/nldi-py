#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""Test suite for nldi-py package"""

import os

import pytest

from nldi import config, openapi


@pytest.mark.order(20)
@pytest.mark.unittest
def test_legacy_generate_alignment(global_config):
    _ = config.align_crawler_sources(global_config)


@pytest.mark.order(21)
@pytest.mark.unittest
def test_legacy_generate_openapi_document(global_config):
    c = openapi.get_oas(global_config)
    ## Just check that the main parts of the dict are present....
    assert c["openapi"] == "3.0.1"
    assert c["info"]["title"] is not None
    assert c["info"]["description"] is not None
    assert c["info"]["license"] is not None

@pytest.mark.order(22)
@pytest.mark.unittest
def test_configuration_load(config_yaml, env_update):
    os.environ.update(env_update)
    c = config.Configuration(config_yaml)
    assert c is not None
    assert c.config_source == str(config_yaml)
    assert c["server"]["data"]["dbname"] == "nldi"
