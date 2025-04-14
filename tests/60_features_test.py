#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
# SPDX-FileCopyrightText: 2024-present USGS
# See the full copyright notice in LICENSE.md
#

"""
Feature Lookups -- Finding source-specific features.

- [+] FeatureSourceModel Repository
    - [+] Get one row from a source (give source_name and identifier)
    - [+] if source doesn't exist? (tested elsewhere under source services)
    - [+] if identifier doesn't exist (but source does)?
    - [+] get all rows for a given source
- [+] FeatureSourceModel Service
    - [+] Get one feature, given source_name and identifier
    - [+] raise exceptions if either source_name or identifier are not found
    - [+] get all features for a source
    - [+] empty list if source doesn't exist; no exception raised.
    - [+] stream all features for a source
    - [+] stream a single feature for a source
    - [+] stream raise NotFoundError if no features selected (due to bad ID or bad source_suffix)
- [ ] Endpoints for litestar API
    - [+] GET f"{API_PREFIX}/linked-data/{source_name}"
      - [+] stream data (all features) as FeatureCollection
      - [+] 404 if source not found
    - [+] GET f"{API_PREFIX}/linked-data/{source_name}/{identifier}"
      - [+] Fetch single source; output as FeatureCollection
      - [+] 404 if source does not exist
      - [+] 404 if feature identifier does not exist

      -

"""

import json

import pytest
from advanced_alchemy.exceptions import NotFoundError

from nldi.db.schemas.nldi_data import FeatureSourceModel
from nldi.domain.linked_data import repos, services

from . import API_PREFIX


# region: repository
@pytest.mark.order(60)
@pytest.mark.unittest
async def test_feature_repo_get(dbsession_containerized) -> None:
    feature_repo = repos.FeatureRepository(session=dbsession_containerized)

    identifier = "USGS-05427930"  # < this ID and source must be in the containerized DB.
    source_name = "WQP"  # NOTE: repo is case-sensitive; the service isn't

    ## "old" lookup method, without association proxies on FeatureSourceModel
    sources_svc = services.CrawlerSourceService(session=dbsession_containerized)
    _src = await sources_svc.get_by_suffix(source_name)
    _feature = await feature_repo.get_one_or_none(
        FeatureSourceModel.identifier == identifier, FeatureSourceModel.crawler_source_id == _src.crawler_source_id
    )

    assert _feature is not None
    assert _feature.comid == 13294176  # < NOTE: integer; not a string
    assert _feature.name.startswith("DORN (SPRING) CREEK")

    ## "new" lookup method, with association proxies to simplify matching the source; i.e. no need to separately lookup source ID.
    _feature = await feature_repo.get_one_or_none(
        FeatureSourceModel.source == source_name, FeatureSourceModel.identifier == identifier
    )

    assert _feature is not None
    assert _feature.comid == 13294176  # < NOTE: integer; not a string
    assert _feature.name.startswith("DORN (SPRING) CREEK")


@pytest.mark.order(60)
@pytest.mark.unittest
async def test_feature_repo_get_notfound(dbsession_containerized) -> None:
    feature_repo = repos.FeatureRepository(session=dbsession_containerized)
    sources_svc = services.CrawlerSourceService(session=dbsession_containerized)

    identifier = "USGS-00000000"
    source_name = "wqp"

    # Invalid source name is tested elsewhere. 40_crawler_sources_test.py
    _src = await sources_svc.get_by_suffix(source_name)
    assert _src.source_suffix.lower() == source_name

    _feature = await feature_repo.get_one_or_none(
        FeatureSourceModel.identifier == identifier,
        FeatureSourceModel.crawler_source_id == _src.crawler_source_id,
    )

    assert _feature is None


@pytest.mark.order(60)
@pytest.mark.unittest
async def test_feature_repo_get_all(dbsession_containerized) -> None:
    feature_repo = repos.FeatureRepository(session=dbsession_containerized)
    sources_svc = services.CrawlerSourceService(session=dbsession_containerized)

    source_name = "WQP"

    # Invalid source name is tested elsewhere. 40_crawler_sources_test.py
    _src = await sources_svc.get_by_suffix(source_name)
    assert _src.source_suffix == source_name

    _features = await feature_repo.list(FeatureSourceModel.crawler_source_id == _src.crawler_source_id)

    assert isinstance(_features, list)
    assert len(_features) > 1


# region: services
@pytest.mark.order(62)
@pytest.mark.integration
async def test_feature_svc_get(dbsession_containerized) -> None:
    feature_svc = services.FeatureService(session=dbsession_containerized)

    identifier = "USGS-05427930"  # < this ID and source must be in the containerized DB.
    source_name = "wqp"

    feature_lower = await feature_svc.feature_lookup(source_name.lower(), identifier)
    assert feature_lower.comid == 13294176

    feature_upper = await feature_svc.feature_lookup(source_name.upper(), identifier)
    assert feature_upper.comid == 13294176


@pytest.mark.order(62)
@pytest.mark.integration
async def test_feature_svc_get_nonesuch_id(dbsession_containerized) -> None:
    feature_svc = services.FeatureService(session=dbsession_containerized)

    # If the ID is bogus, but source is good:
    identifier = "USGS-00000000"
    source_name = "wqp"
    with pytest.raises(NotFoundError):
        _feature = await feature_svc.feature_lookup(source_name, identifier)

    # if the ID is good, but the source is not:
    identifier = "USGS-05427930"
    source_name = "nonesuch"
    with pytest.raises(NotFoundError):
        _feature = await feature_svc.feature_lookup(source_name, identifier)


@pytest.mark.order(62)
@pytest.mark.integration
async def test_feature_svc_list_all(dbsession_containerized) -> None:
    feature_svc = services.FeatureService(session=dbsession_containerized)
    source_name = "wqp"
    _all_features = await feature_svc.list_by_src(source_name)
    assert isinstance(_all_features, list)
    assert len(_all_features) > 1

    _all_features = await feature_svc.list_by_src(source_name.upper())
    assert isinstance(_all_features, list)
    assert len(_all_features) > 1


@pytest.mark.order(62)
@pytest.mark.integration
async def test_feature_svc_list_all_bad_src(dbsession_containerized) -> None:
    feature_svc = services.FeatureService(session=dbsession_containerized)
    source_name = "nonesuch"
    _all_features = await feature_svc.list_by_src(source_name)
    assert isinstance(_all_features, list)
    assert len(_all_features) == 0


@pytest.mark.order(62)
@pytest.mark.integration
async def test_feature_svc_get_features_get_stream(dbsession_containerized) -> None:
    feature_svc = services.FeatureService(session=dbsession_containerized)
    source_name = "wqp"
    identifier = "USGS-05427930"
    # feature_collection_stream is a generator... need to exhaust it in order to get the full result.
    streamed_str = ""
    async for chunk in feature_svc.feature_collection_stream(source_name, identifier):
        streamed_str += chunk.decode("utf-8")

    actual = json.loads(streamed_str)
    features = actual["features"]
    assert isinstance(features, list)
    assert len(features) == 1


@pytest.mark.order(62)
@pytest.mark.integration
async def test_feature_svc_get_features_get_nonesuch_stream(dbsession_containerized) -> None:
    feature_svc = services.FeatureService(session=dbsession_containerized)
    source_name = "wqp"
    identifier = "USGS-0542793x"
    with pytest.raises(NotFoundError):
        streamed_str = ""
        async for chunk in feature_svc.feature_collection_stream(source_name, identifier):
            streamed_str += chunk.decode("utf-8")


@pytest.mark.order(62)
@pytest.mark.integration
async def test_feature_svc_get_features_list_stream(dbsession_containerized) -> None:
    feature_svc = services.FeatureService(session=dbsession_containerized)
    source_name = "wqp"
    streamed_str = ""
    async for chunk in feature_svc.feature_collection_stream(source_name.lower()):
        streamed_str += chunk.decode("utf-8")

    actual = json.loads(streamed_str)
    features = actual["features"]
    assert isinstance(features, list)
    assert len(features) >= 1

    ## Do it all again with the upcase version of the source name... result should be the same.
    streamed_str = ""
    async for chunk in feature_svc.feature_collection_stream(source_name.upper()):
        streamed_str += chunk.decode("utf-8")

    actual = json.loads(streamed_str)
    features = actual["features"]
    assert isinstance(features, list)
    assert len(features) >= 1


# region: litestar endpoints


@pytest.mark.order(65)
@pytest.mark.integration
def test_api_get_feature_by_identifier(client_containerized) -> None:
    identifier = "USGS-05427930"
    source_name = "wqp"

    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name}/{identifier}?f=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")

    actual = r.json()  # Should return a feature collection as JSON
    assert actual["type"] == "FeatureCollection"
    features = actual["features"]
    assert isinstance(features, list)
    assert len(features) == 1


@pytest.mark.order(65)
@pytest.mark.integration
def test_api_get_feature_by_id_notfound(client_containerized) -> None:
    identifier = "USGS-05427930"
    source_name = "nonesuch"

    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name}/{identifier}?f=json")
    assert r.status_code == 404

    identifier = "USGS-xxxxxxxx"
    source_name = "wqp"

    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name}/{identifier}?f=json")
    assert r.status_code == 404


@pytest.mark.order(65)
@pytest.mark.integration
def test_api_list_features_by_source(client_containerized) -> None:
    source_name = "wqp"

    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name.lower()}?f=json")
    assert r.status_code == 200
    actual = r.json()
    assert actual["type"] == "FeatureCollection"
    features_lowcase = actual["features"]
    assert isinstance(features_lowcase, list)
    assert len(features_lowcase) > 1

    ## Do it again as upcase...
    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name.upper()}?f=json")
    assert r.status_code == 200
    actual = r.json()
    assert actual["type"] == "FeatureCollection"
    features_upcase = actual["features"]
    assert isinstance(features_upcase, list)
    assert len(features_upcase) == len(features_lowcase)


@pytest.mark.order(69)  # TODO: Implement - depends on pygeoapi
@pytest.mark.integration
def test_api_get_basin_by_id(client_containerized) -> None:
    # NOTE: At this point, we are merely testing that the endpoint exists.  It should return a HTTP 501 (NOT_IMPLEMENTED) for now.
    source_name = "wqp"
    identifier = "USGS-05427930"

    r = client_containerized.get(f"{API_PREFIX}/linked-data/{source_name}/{identifier}/basin?f=json")
    assert r.status_code == 501
    assert r.headers["content-type"].startswith("application/json")

    extra = r.json()["extra"]
    return None
