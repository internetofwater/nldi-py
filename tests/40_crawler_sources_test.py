#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
# + = Done
# - = Not Done
# o = In-Process
# X = FAILING

"""
Crawler Sources

- [+] CrawlerSource Repository
    + Health Check
    + Can fetch by primary key (id)
    + Can lookup by suffix (valid)
    + Can lookup by suffix (KeyError)
    + Can list all
- [ ] CrawlerSource Service
    - Pass-through to repo for most requests
    - Can handle case-insensitive suffix search
- [+] CrawlerSource Endpoint(s)
    - [+] GET f"{API_PREFIX}/linked-data"
        + list all

"""

import pytest
from advanced_alchemy.exceptions import NotFoundError
from sqlalchemy import func

from nldi.db.schemas.nldi_data import CrawlerSourceModel
from nldi.server.linked_data import repos, services

from . import API_PREFIX


# region: respository
@pytest.mark.order(40)
@pytest.mark.unittest
async def test_source_repo_get_by_id(dbsession_containerized) -> None:
    src_repo = repos.CrawlerSourceRepository(session=dbsession_containerized)
    healthy = await src_repo.check_health(src_repo.session)
    assert healthy

    feature = await src_repo.get(1)
    assert feature is not None


@pytest.mark.order(40)
@pytest.mark.unittest
async def test_source_repo_lookup_by_suffix(dbsession_containerized) -> None:
    src_repo = repos.CrawlerSourceRepository(session=dbsession_containerized)

    feature = await src_repo.get_one_or_none(
        func.lower(CrawlerSourceModel.source_suffix) == "WQP".lower(),
    )
    assert feature.crawler_source_id == 1  # < known value for this source.


@pytest.mark.order(40)
@pytest.mark.unittest
async def test_source_repo_lookup_by_suffix_nonesuch(dbsession_containerized) -> None:
    src_repo = repos.CrawlerSourceRepository(session=dbsession_containerized)

    feature = await src_repo.get_one_or_none(CrawlerSourceModel.source_suffix == "nonesuch")
    assert feature is None


@pytest.mark.order(40)
@pytest.mark.unittest
async def test_source_repo_listall(dbsession_containerized) -> None:
    src_repo = repos.CrawlerSourceRepository(session=dbsession_containerized)
    features, count = await src_repo.list_and_count()
    assert count == 3  # < true for the containerized db
    assert isinstance(features, list)
    assert isinstance(features[0], CrawlerSourceModel)


# region: service layer
@pytest.mark.order(42)
@pytest.mark.unittest
async def test_source_service_search_by_suffix(dbsession_containerized) -> None:
    src_svc = services.CrawlerSourceService(session=dbsession_containerized)

    feature = await src_svc.get_by_suffix("wqp")
    assert feature.source_suffix.lower() == "wqp"

    ## Case insensitive:
    feature = await src_svc.get_by_suffix("WQP")
    assert feature.source_suffix.lower() == "wqp"

    ## weird case:
    feature = await src_svc.get_by_suffix("wQp")
    assert feature.source_suffix.lower() == "wqp"


@pytest.mark.order(42)
@pytest.mark.unittest
async def test_source_service_search_by_suffix_nonesuch(dbsession_containerized) -> None:
    src_svc = services.CrawlerSourceService(session=dbsession_containerized)

    with pytest.raises(NotFoundError):
        feature = await src_svc.get_by_suffix("nonesuch")


@pytest.mark.order(43)
@pytest.mark.unittest
async def test_source_service_suffix_exists(dbsession_containerized) -> None:
    src_svc = services.CrawlerSourceService(session=dbsession_containerized)

    actual = await src_svc.suffix_exists("wqp")
    assert actual is True

    actual = await src_svc.suffix_exists("WQP")
    assert actual is True

    actual = await src_svc.suffix_exists("nonesuch")
    assert actual is False


@pytest.mark.order(45)
@pytest.mark.unittest
def test_source_list_endpoint(f_client_containerized) -> None:
    r = f_client_containerized.get(f"{API_PREFIX}/linked-data?f=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")

    actual = r.json
    assert isinstance(actual, list)
    assert len(actual) == 3  # < true for containerized db
