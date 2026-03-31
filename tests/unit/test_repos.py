from unittest.mock import AsyncMock


def test_repos_instantiate():
    from nldi.db.repos import CatchmentRepository, CrawlerSourceRepository, FeatureRepository, FlowlineRepository

    session = AsyncMock()
    assert CrawlerSourceRepository(session=session) is not None
    assert FeatureRepository(session=session) is not None
    assert FlowlineRepository(session=session) is not None
    assert CatchmentRepository(session=session) is not None
