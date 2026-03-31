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
