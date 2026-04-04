"""Integration tests for flowline navigation."""

import pytest
from sqlalchemy import text


@pytest.mark.integration
async def test_dm_navigation_returns_flowlines(db_session):
    """DM navigation from a known comid should return multiple flowlines."""
    from nldi.db.navigation import dm
    from nldi.db.models import FlowlineModel
    from sqlalchemy import select

    nav_query = dm(comid=13293396, distance=10)
    subq = nav_query.subquery()
    stmt = select(FlowlineModel.nhdplus_comid).join(subq, FlowlineModel.nhdplus_comid == subq.c.comid)
    result = await db_session.execute(stmt)
    comids = [row[0] for row in result]
    assert len(comids) > 0
    assert 13293396 in comids  # starting comid should be in results


@pytest.mark.integration
@pytest.mark.parametrize("mode_fn,mode_name", [
    ("dm", "DM"),
    ("dd", "DD"),
    ("um", "UM"),
    ("ut", "UT"),
])
async def test_all_nav_modes_return_results(db_session, mode_fn, mode_name):
    """Each navigation mode should return at least the starting comid."""
    from nldi.db import navigation
    from nldi.db.models import FlowlineModel
    from sqlalchemy import select

    fn = getattr(navigation, mode_fn)
    nav_query = fn(comid=13293396, distance=10)
    subq = nav_query.subquery()
    stmt = select(FlowlineModel.nhdplus_comid).join(subq, FlowlineModel.nhdplus_comid == subq.c.comid)
    result = await db_session.execute(stmt)
    comids = [row[0] for row in result]
    assert len(comids) > 0, f"{mode_name} returned no results"
