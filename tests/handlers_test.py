#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

import pytest

@pytest.mark.order(20)
@pytest.mark.integration
def test_base_handler(nldi_db_container):
    from nldi.handlers import BaseHandler

    bh = BaseHandler(nldi_db_container)
    with pytest.raises(NotImplementedError):
        bh.get("test")
    assert bh._heartbeat()


@pytest.mark.order(21)
@pytest.mark.integration
def test_crawler_source_handler(nldi_db_container):
    from nldi.handlers import CrawlerSourceHandler
    csh = CrawlerSourceHandler(nldi_db_container)
    _tmp = csh.get("WQP")
    assert _tmp['source_name'] == "Water Quality Portal"
