def test_datasource_dto():
    from nldi.dto import DataSource

    ds = DataSource(source="wqp", sourceName="Water Quality Portal", features="https://example.com/linked-data/wqp")
    assert ds.source == "wqp"
    assert ds.sourceName == "Water Quality Portal"
    assert ds.features == "https://example.com/linked-data/wqp"
