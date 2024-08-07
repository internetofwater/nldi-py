#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
import os

import pytest
from nldi import util
from nldi.handlers import BaseHandler, CrawlerSourceHandler, FeatureHandler
from nldi.handlers.errors import ProviderItemNotFoundError


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
def test_align_sources(global_config):
    sources = global_config["sources"]
    csh = CrawlerSourceHandler({"database": global_config["server"]["data"]})
    assert csh.align_sources(sources)


@pytest.mark.order(23)
@pytest.mark.unittest
def test_handler_feature(mock_source, nldi_db_container):
    """
    Sample feature lookup from a given source.

    Lifted from the feature_wqp table in the nldi database:
    |crawler_source_id|identifier        |name                                            |uri                                                                         |location                  |comid     |reachcode|measure|shape|
    |-----------------|------------------|------------------------------------------------|----------------------------------------------------------------------------|--------------------------|----------|---------|-------|-----|
    |1                |WIDNR_WQX-10039694|Unnamed Trib (807500) Yahara R at Cuba Valley Rd|http://www.waterqualitydata.us/provider/STORET/WIDNR_WQX/WIDNR_WQX-10039694/|POINT (-89.38764 43.22121)|13,293,452|         |       |     |

    """
    fh = FeatureHandler({"source": mock_source, "database": nldi_db_container, "base_url": "http://localhost/nldi"})
    assert fh is not None
    feature_dict = fh.get("WIDNR_WQX-10039694")
    # assert feature_dict == {}
    assert feature_dict["properties"]["identifier"] == "WIDNR_WQX-10039694"
    assert feature_dict["properties"]["name"] == "Unnamed Trib (807500) Yahara R at Cuba Valley Rd"


"""
Another test possibility... nwissite
|crawler_source_id|identifier|name    |uri                                                     |location                                    |comid     |reachcode     |measure |shape|
|-----------------|----------|--------|--------------------------------------------------------|--------------------------------------------|----------|--------------|--------|-----|
|2                |05428500  |05428500|http://waterdata.usgs.gov/nwis/nwisman/?site_no=05428500|POINT (-89.36087179991962 43.08945814192896)|13,293,750|07090002007373|42.85815|     |

"""


@pytest.mark.order(23)
@pytest.mark.unittest
def test_handler_feature_notfound(mock_source, nldi_db_container):
    """
    Sample feature lookup from a given source, with known missing identifier."""
    fh = FeatureHandler({"source": mock_source, "database": nldi_db_container, "base_url": "http://localhost/nldi"})
    assert fh is not None
    with pytest.raises(ProviderItemNotFoundError):
        feature_dict = fh.get("NO_SUCH_FEATURE_WITH_THIS_IDENTIFIER")


@pytest.mark.order(23)
@pytest.mark.unittest
def test_handler_feature_getall(mock_source, nldi_db_container):
    """Get all features crawled from a given source."""
    fh = FeatureHandler({"source": mock_source, "database": nldi_db_container, "base_url": "http://localhost/nldi"})
    assert fh is not None
    feature_list = list(fh.query()) #<< must cast to a list; otherwise, it's a generator
    assert len(feature_list) == 1105  # WQP is known to have this number of features in the demo database
