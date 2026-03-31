"""Unit test fixtures."""

import pytest


class FakeSource:
    """Minimal stand-in for CrawlerSourceModel."""

    def __init__(self, source_suffix: str, source_name: str):
        self.source_suffix = source_suffix
        self.source_name = source_name


class FakeCrawlerSourceRepository:
    """Fake CrawlerSourceRepository for unit tests."""

    def __init__(self, sources: list | None = None):
        self._sources = sources or []

    async def list(self, **kwargs) -> list:
        """Return canned sources."""
        return self._sources


@pytest.fixture()
def fake_source_repo():
    """Provide a FakeCrawlerSourceRepository factory."""
    return FakeCrawlerSourceRepository


@pytest.fixture()
def make_source():
    """Provide a FakeSource factory."""
    return FakeSource
