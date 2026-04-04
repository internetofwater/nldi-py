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


def test_dd_returns_select():
    from nldi.db.navigation import dd

    query = dd(comid=13293396, distance=10)
    assert isinstance(query, Select)


def test_um_returns_select():
    from nldi.db.navigation import um

    query = um(comid=13293396, distance=10)
    assert isinstance(query, Select)


def test_ut_returns_select():
    from nldi.db.navigation import ut

    query = ut(comid=13293396, distance=10)
    assert isinstance(query, Select)


def test_navigation_query_dispatches():
    from nldi.db.navigation import navigation_query

    for mode in ("DM", "DD", "UM", "UT"):
        query = navigation_query(mode, comid=123, distance=10)
        assert isinstance(query, Select)


def test_navigation_query_invalid_mode():
    import pytest

    from nldi.db.navigation import navigation_query

    with pytest.raises(ValueError, match="Invalid navigation mode"):
        navigation_query("BOGUS", comid=123, distance=10)
