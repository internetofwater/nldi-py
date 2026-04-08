"""Integration tests for repository methods against real DB.

Covers repo methods called by controllers that were previously
only tested with fakes.
"""

import pytest
import sqlalchemy

from nldi.db.models import CatchmentModel, CrawlerSourceModel, FlowlineModel
from nldi.db.repos import (
    CatchmentRepository,
    CrawlerSourceRepository,
    FeatureRepository,
    FlowlineRepository,
)

KNOWN_COMID = 13293396
KNOWN_SOURCE = "wqp"
KNOWN_FEATURE = "USGS-05427930"


@pytest.mark.integration
class TestCrawlerSourceRepo:
    async def test_list_all(self, db_session):
        repo = CrawlerSourceRepository(session=db_session)
        sources = await repo.list()
        assert len(sources) > 0

    async def test_get_by_suffix(self, db_session):
        repo = CrawlerSourceRepository(session=db_session)
        source = await repo.get_by_suffix(KNOWN_SOURCE)
        assert source is not None
        assert source.source_suffix.lower() == KNOWN_SOURCE

    async def test_get_by_suffix_case_insensitive(self, db_session):
        repo = CrawlerSourceRepository(session=db_session)
        source = await repo.get_by_suffix("WQP")
        assert source is not None


@pytest.mark.integration
class TestFlowlineRepo:
    async def test_get_one_or_none_by_comid(self, db_session):
        repo = FlowlineRepository(session=db_session)
        flowline = await repo.get_one_or_none(FlowlineModel.nhdplus_comid == KNOWN_COMID)
        assert flowline is not None
        assert flowline.nhdplus_comid == KNOWN_COMID

    async def test_get_one_or_none_missing(self, db_session):
        repo = FlowlineRepository(session=db_session)
        flowline = await repo.get_one_or_none(FlowlineModel.nhdplus_comid == -1)
        assert flowline is None

    async def test_get_measure_and_reachcode(self, db_session):
        repo = FlowlineRepository(session=db_session)
        measure, reachcode = await repo.get_measure_and_reachcode(
            KNOWN_COMID, "POINT(-89.4423056 43.1402778)"
        )
        assert measure is not None
        assert reachcode is not None


@pytest.mark.integration
class TestFeatureRepo:
    async def test_feature_lookup(self, db_session):
        repo = FeatureRepository(session=db_session)
        feat = await repo.feature_lookup(KNOWN_SOURCE, KNOWN_FEATURE)
        assert feat is not None
        assert feat.identifier == KNOWN_FEATURE

    async def test_list_by_source(self, db_session):
        repo = FeatureRepository(session=db_session)
        features = await repo.list_by_source(KNOWN_SOURCE, limit=5)
        assert len(features) > 0
        assert len(features) <= 5


@pytest.mark.integration
class TestCatchmentRepo:
    async def test_get_by_point(self, db_session):
        repo = CatchmentRepository(session=db_session)
        catchment = await repo.get_by_point("POINT(-89.4423056 43.1402778)")
        assert catchment is not None
