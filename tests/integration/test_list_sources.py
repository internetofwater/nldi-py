"""Integration tests for GET /linked-data (list sources)."""

import pytest
from sqlalchemy import text


@pytest.mark.integration
async def test_sources_table_has_data(db_session):
    """Verify the test container has crawler_source data."""
    result = await db_session.execute(text("SELECT count(*) FROM nldi_data.crawler_source"))
    count = result.scalar()
    assert count > 0


@pytest.mark.integration
async def test_list_sources_from_repo(db_session):
    """Verify CrawlerSourceRepository returns sources with expected shape."""
    from nldi.db.repos import CrawlerSourceRepository

    repo = CrawlerSourceRepository(session=db_session)
    sources = await repo.list()
    assert len(sources) > 0
    for s in sources:
        assert s.source_suffix is not None
        assert s.source_name is not None
