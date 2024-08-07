#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
import os

import pytest
from nldi import util
from nldi.handlers import BaseHandler, CrawlerSourceHandler


@pytest.mark.order(20)
@pytest.mark.integration
def test_handler_base(nldi_db_container):
    """Test BaseHandler class."""
    _def = {"database": nldi_db_container}
    bh = BaseHandler(_def)
    with pytest.raises(NotImplementedError):
        bh.get("test")
    assert bh._heartbeat()  # << Verifies that we can connect for simple "SELECT 1" query


@pytest.mark.order(21)
@pytest.mark.integration
@pytest.mark.parametrize(  # Known sources and their names.  Should pull from crawler_sources table to match.
    "source,name",
    [
        ("WQP", "Water Quality Portal"),
        ("nwissite", "NWIS Surface Water Sites"),
        ("huc12pp", "HUC12 Pour Points"),
    ],
)
def test_handler_crawlersource(nldi_db_container, source, name):
    _def = {"database": nldi_db_container}
    csh = CrawlerSourceHandler(_def)
    result = csh.get(source)
    assert result["source_name"] == name


@pytest.mark.order(22)
@pytest.mark.integration
def test_align_sources(nldi_db_container, config_yaml, env_update):
    os.environ.update(env_update)
    cfg = util.load_yaml(config_yaml)
    sources = cfg["sources"]
    _def = {"database": nldi_db_container}
    csh = CrawlerSourceHandler(_def)
    assert csh.align_sources(sources)
