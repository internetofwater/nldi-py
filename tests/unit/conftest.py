"""Unit test fixtures."""

import pytest


class FakeSource:
    """Minimal stand-in for CrawlerSourceModel."""

    def __init__(self, source_suffix: str, source_name: str):
        self.source_suffix = source_suffix
        self.source_name = source_name


class FakeFeatureModel:
    """Minimal stand-in for FeatureSourceModel."""

    def __init__(self, identifier: str, source_suffix: str, source_name: str, name: str, uri: str):
        self.identifier = identifier
        self.name = name
        self.uri = uri
        self.comid = None
        self.reachcode = None
        self.measure = None
        self.location = None
        # Simulate association proxies
        self.source_suffix_proxy = source_suffix
        self.source_name_proxy = source_name
        self.feature_type_proxy = "point"
        self.mainstem = None


class FakeFlowlineModel:
    """Minimal stand-in for FlowlineModel."""

    def __init__(self, nhdplus_comid: int, shape_geojson: str = '{"type":"LineString","coordinates":[[-89,43],[-89.1,43.1]]}'):
        self.nhdplus_comid = nhdplus_comid
        self.shape_geojson = shape_geojson
        self.permanent_identifier = str(nhdplus_comid)
        self.reachcode = "00000000000000"
        self.fmeasure = 0.0
        self.tmeasure = 100.0
        self.mainstem = None


class FakeCrawlerSourceRepository:
    """Fake CrawlerSourceRepository for unit tests."""

    def __init__(self, sources: list | None = None):
        self._sources = sources or []

    async def list(self, **kwargs) -> list:
        """Return canned sources."""
        return self._sources

    async def get_one_or_none(self, *args, **kwargs) -> FakeSource | None:
        """Find a source by suffix."""
        suffix = kwargs.get("source_suffix", "")
        for s in self._sources:
            if s.source_suffix.lower() == suffix.lower():
                return s
        return None

    async def get_by_suffix(self, suffix: str) -> FakeSource | None:
        """Find a source by suffix, case-insensitive."""
        for s in self._sources:
            if s.source_suffix.lower() == suffix.lower():
                return s
        return None


class FakeFeatureRepository:
    """Fake FeatureRepository for unit tests."""

    def __init__(self, features: list | None = None):
        self._features = features or []

    async def feature_lookup(self, source_suffix: str, identifier: str) -> FakeFeatureModel | None:
        """Find a feature by source and identifier."""
        for f in self._features:
            if f.identifier == identifier:
                return f
        return None

    async def list_by_source(self, source_suffix: str, limit: int = 0, offset: int = 0) -> list:
        """List features for a source with pagination."""
        results = [f for f in self._features if f.source_suffix_proxy.lower() == source_suffix.lower()]
        results = results[offset:]
        if limit > 0:
            results = results[:limit]
        return results


class FakeFlowlineRepository:
    """Fake FlowlineRepository for unit tests."""

    def __init__(self, flowlines: list | None = None):
        self._flowlines = flowlines or []

    async def get(self, id, **kwargs) -> FakeFlowlineModel | None:
        """Find a flowline by comid."""
        for f in self._flowlines:
            if f.nhdplus_comid == int(id):
                return f
        return None

    async def get_one_or_none(self, *args, **kwargs) -> FakeFlowlineModel | None:
        """Find a flowline by comid."""
        comid = kwargs.get("nhdplus_comid")
        if comid is None:
            return None
        for f in self._flowlines:
            if f.nhdplus_comid == int(comid):
                return f
        return None

    async def list_all(self, limit: int = 0, offset: int = 0) -> list:
        """List flowlines with pagination."""
        results = self._flowlines[offset:]
        if limit > 0:
            results = results[:limit]
        return results


@pytest.fixture()
def fake_source_repo():
    """Provide a FakeCrawlerSourceRepository factory."""
    return FakeCrawlerSourceRepository


@pytest.fixture()
def make_source():
    """Provide a FakeSource factory."""
    return FakeSource


@pytest.fixture()
def fake_feature_repo():
    """Provide a FakeFeatureRepository factory."""
    return FakeFeatureRepository


@pytest.fixture()
def make_feature():
    """Provide a FakeFeatureModel factory."""
    return FakeFeatureModel


@pytest.fixture()
def fake_flowline_repo():
    """Provide a FakeFlowlineRepository factory."""
    return FakeFlowlineRepository


@pytest.fixture()
def make_flowline():
    """Provide a FakeFlowlineModel factory."""
    return FakeFlowlineModel
