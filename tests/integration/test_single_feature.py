"""Integration tests for GET /linked-data/{source}/{identifier} (single feature)."""

import os

import pytest
from sqlalchemy import text


@pytest.mark.integration
async def test_feature_lookup_by_source_and_id(db_session):
    """Verify a known feature exists in the test container."""
    result = await db_session.execute(
        text("SELECT identifier FROM nldi_data.feature WHERE identifier = 'USGS-05427930' LIMIT 1")
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "USGS-05427930"


@pytest.mark.integration
async def test_flowline_lookup_by_comid(db_session):
    """Verify a known flowline exists in the test container."""
    result = await db_session.execute(
        text("SELECT nhdplus_comid FROM nhdplus.nhdflowline_np21 WHERE nhdplus_comid = 13293396 LIMIT 1")
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == 13293396
