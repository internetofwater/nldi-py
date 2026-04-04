"""Unit tests for navigation query builder."""

from sqlalchemy.sql import Select


def test_navigation_modes_import():
    from nldi.db.navigation import NavigationModes

    assert "DM" in NavigationModes.__members__
    assert "DD" in NavigationModes.__members__
    assert "UM" in NavigationModes.__members__
    assert "UT" in NavigationModes.__members__


def test_dm_returns_select():
    from nldi.db.navigation import dm

    query = dm(comid=13293396, distance=10)
    assert isinstance(query, Select)
