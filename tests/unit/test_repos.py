from unittest.mock import AsyncMock


def test_repos_instantiate():
    from nldi.db.repos import CatchmentRepository, CrawlerSourceRepository, FeatureRepository, FlowlineRepository

    session = AsyncMock()
    assert CrawlerSourceRepository(session=session) is not None
    assert FeatureRepository(session=session) is not None
    assert FlowlineRepository(session=session) is not None
    assert CatchmentRepository(session=session) is not None


def test_get_drainage_basin_uses_characteristic_data():
    """get_drainage_basin must join on characteristic_data.catchmentsp, not nhdplus."""
    import inspect as _inspect

    from nldi.db.repos import CatchmentRepository

    source = _inspect.getsource(CatchmentRepository.get_drainage_basin)
    assert "CharacteristicCatchmentModel" in source, "get_drainage_basin should use CharacteristicCatchmentModel"


def test_catchment_repository_model_type_is_nhdplus():
    """Characterization: CatchmentRepository.model_type must remain nhdplus.CatchmentModel."""
    from nldi.db.models import CatchmentModel
    from nldi.db.repos import CatchmentRepository

    assert CatchmentRepository.model_type is CatchmentModel
    assert CatchmentModel.metadata.schema == "nhdplus"
