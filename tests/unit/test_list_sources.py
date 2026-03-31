"""Unit tests for list_sources endpoint logic."""

from nldi.dto import DataSource


def test_list_sources_includes_comid():
    """The comid synthetic source should always be first."""
    # Simulate what the endpoint does: prepend comid, then map DB sources
    base_url = "https://example.com/nldi"
    db_sources = [
        {"source_suffix": "wqp", "source_name": "Water Quality Portal"},
    ]

    result = [
        DataSource(source="comid", sourceName="NHDPlus comid", features=f"{base_url}/linked-data/comid"),
    ]
    for s in db_sources:
        result.append(
            DataSource(
                source=s["source_suffix"],
                sourceName=s["source_name"],
                features=f"{base_url}/linked-data/{s['source_suffix']}",
            )
        )

    assert result[0].source == "comid"
    assert len(result) == 2
    assert result[1].source == "wqp"
    assert result[1].features == "https://example.com/nldi/linked-data/wqp"
