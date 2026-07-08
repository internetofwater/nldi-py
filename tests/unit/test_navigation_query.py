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


def test_basin_query_uses_characteristic_data():
    from nldi.db.navigation import basin_query

    query = basin_query(13293396)
    sql = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert "characteristic_data.plusflowlinevaa_np21" in sql
    assert "nhdplus.plusflowlinevaa_np21" not in sql


def test_navigation_ctes_use_nhdplus():
    """Characterization: dm, dd, um, ut must use nhdplus, not characteristic_data."""
    from nldi.db.navigation import dd, dm, um, ut

    for builder in (dm, dd, um, ut):
        query = builder(comid=13293396, distance=10)
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))
        assert "nhdplus.plusflowlinevaa_np21" in sql, f"{builder.__name__} missing nhdplus reference"
        assert "characteristic_data" not in sql, f"{builder.__name__} should not reference characteristic_data"
