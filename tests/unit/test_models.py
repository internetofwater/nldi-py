def test_all_models_import():
    from nldi.db.models import (
        CatchmentModel,
        CrawlerSourceModel,
        FeatureSourceModel,
        FlowlineModel,
        FlowlineVAAModel,
        MainstemLookupModel,
    )

    assert CrawlerSourceModel.__tablename__ == "crawler_source"
    assert FeatureSourceModel.__tablename__ == "feature"
    assert MainstemLookupModel.__tablename__ == "mainstem_lookup"
    assert FlowlineModel.__tablename__ == "nhdflowline_np21"
    assert FlowlineVAAModel.__tablename__ == "plusflowlinevaa_np21"
    assert CatchmentModel.__tablename__ == "catchmentsp"


def test_characteristic_data_base_model_schema():
    from nldi.db.models import CharacteristicDataBaseModel

    assert CharacteristicDataBaseModel.metadata.schema == "characteristic_data"


def test_characteristic_catchment_model():
    from sqlalchemy import inspect

    from nldi.db.models import CharacteristicCatchmentModel

    assert CharacteristicCatchmentModel.__tablename__ == "catchmentsp"
    assert CharacteristicCatchmentModel.metadata.schema == "characteristic_data"
    columns = {c.key for c in inspect(CharacteristicCatchmentModel).mapper.column_attrs}
    assert columns == {"ogc_fid", "featureid", "the_geom"}


def test_characteristic_flowline_vaa_model():
    from nldi.db.models import CharacteristicFlowlineVAAModel

    assert CharacteristicFlowlineVAAModel.__tablename__ == "plusflowlinevaa_np21"
    assert CharacteristicFlowlineVAAModel.metadata.schema == "characteristic_data"
