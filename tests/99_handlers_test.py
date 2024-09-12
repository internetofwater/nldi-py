#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
import os

import pytest

from nldi import config, util
from nldi.handlers import (
    BaseHandler,
    CatchmentHandler,
    CrawlerSourceHandler,
    FeatureHandler,
    FlowlineHandler,
    MainstemHandler,
)
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
    feature_list = list(fh.query())  # << must cast to a list; otherwise, it's a generator
    assert len(feature_list) == 1105  # WQP is known to have this number of features in the demo database


@pytest.mark.order(24)
@pytest.mark.unittest
def test_handler_flowline(nldi_db_container):
    """
    |objectid |permanent_identifier|nhdplus_comid|fdate                  |resolution|gnis_id|gnis_name   |lengthkm   |reachcode     |flowdir|wbarea_permanent_identifier|wbarea_nhdplus_comid|ftype|fcode |reachsmdate            |fmeasure|tmeasure|wbarea_ftype|wbarea_fcode|wbd_huc12   |wbd_huc12_percent|catchment_featureid|nhdplus_region|nhdplus_version|navigable|streamlevel|streamorder|hydroseq   |levelpathid|terminalpathid|uphydroseq |dnhydroseq |closed_loop|gdb_geomattr_data|shape                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
    |---------|--------------------|-------------|-----------------------|----------|-------|------------|-----------|--------------|-------|---------------------------|--------------------|-----|------|-----------------------|--------|--------|------------|------------|------------|-----------------|-------------------|--------------|---------------|---------|-----------|-----------|-----------|-----------|--------------|-----------|-----------|-----------|-----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    |2,527,212|13297204            |13,297,204   |2009-05-01 00:00:00.000|3         |1577073|Yahara River|5.133068271|07090002007368|1      |120049283                  |120,049,283         |558  |55,800|2012-06-01 00:00:00.000|22.68468|48.58468|460         |46,006      |070900020904|1                |                   |07            |021_04         |Y        |3          |4          |510,016,313|510,014,902|350,002,977   |510,016,476|510,016,153|           |[BLOB[]]         |LINESTRING M(-89.21126860380173 42.88166259974241 48.584700000006706, -89.2112458050251 42.88164109736681 48.56939999999304, -89.21127250045538 42.87948889285326 47.3640000000014, -89.21006230264902 42.87861839681864 46.66659999999683, -89.20639180392027 42.87829279899597 45.14280000000144, -89.20526030659676 42.8785030990839 44.661900000006426, -89.20348400622606 42.879621893167496 43.698199999998906, -89.2021947056055 42.87955469638109 43.165500000002794, -89.20116870105267 42.87869369983673 42.52419999999984, -89.20069540292025 42.87786149978638 42.01889999999548, -89.20098580420017 42.87491549551487 40.36460000000079, -89.20014410465956 42.87406409531832 39.77490000000398, -89.19924970716238 42.873748295009136 39.36609999999928, -89.1978820040822 42.8726002946496 38.5109999999986, -89.19708000123501 42.87134709954262 37.73510000000533, -89.19605430215597 42.870486095547676 37.093800000002375, -89.1960807070136 42.87021829932928 36.94340000000375, -89.19162290543318 42.866620898246765 34.216599999999744, -89.18832240253687 42.86442969739437 32.38430000000517, -89.18538940697908 42.86414189636707 31.164499999998952, -89.18400890380144 42.8631276935339 30.360499999995227, -89.18044520169497 42.861730098724365 28.695800000001327, -89.17976160347462 42.86115599423647 28.26829999999609, -89.17968340218067 42.86007509380579 27.661999999996624, -89.17917070537806 42.8596445992589 27.341400000004796, -89.17806600034237 42.85958679765463 26.884799999999814, -89.17767120152712 42.85983529686928 26.670700000002398, -89.17527750134468 42.85971009731293 25.681400000001304, -89.17347460240126 42.86109630018473 24.606599999999162, -89.17255400121212 42.86104819923639 24.22609999999986, -89.17062130570412 42.86000479757786 23.237999999997555, -89.16935890167952 42.8596695959568 22.684699999997974)|
    """
    flh = FlowlineHandler({"database": nldi_db_container, "base_url": "http://localhost/nldi"})
    assert flh is not None
    feature_dict = flh.get("13297204")
    assert feature_dict["type"] == "Feature"
    assert feature_dict["properties"]["comid"] == 13297204  ##<<<< note that this is an int, not a str


@pytest.mark.order(24)
@pytest.mark.unittest
def test_handler_flowline_notfound(nldi_db_container):
    flh = FlowlineHandler({"database": nldi_db_container, "base_url": "http://localhost/nldi"})
    assert flh is not None
    with pytest.raises(ProviderItemNotFoundError):
        feature_dict = flh.get(
            "00"
        )  # << note that the identifier must be an int or something that can be cast to an int.


@pytest.mark.order(25)
@pytest.mark.unittest
def test_handler_catchment_query(nldi_db_container):
    # -89.22401470690966 42.82769689708948
    ch = CatchmentHandler({"database": nldi_db_container, "base_url": "http://localhost/nldi"})
    assert ch is not None
    feature_lookup = ch.query("POINT(-89.22401470690966 42.82769689708948)", asGeoJSON=False)
    assert feature_lookup == 13297332  # << known comid for this point

    ## TODO:  Need to figure out how to test the Geo against the catchmentsp table.
    # feature_lookup = ch.query("POINT(-89.22401470690966 42.82769689708948)", asGeoJSON=True)
    # assert feature_lookup["type"] == "Feature"
    # assert feature_lookup["properties"]["comid"] == 13297332


@pytest.mark.order(26)
@pytest.mark.unittest
def test_handler_mainstem(nldi_db_container):
    """
    13294300	467897	https://geoconnex.us/ref/mainstems/467897
    """
    mh = MainstemHandler({"database": nldi_db_container})
    assert mh is not None
    feature_dict = mh.get("13294300")  # << Note that I'm using a string here... but the keys are ints
    assert feature_dict["nhdpv2_comid"] == 13294300  # << int
    assert feature_dict["mainstem_id"] == 467897  # << int
