#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
'Smoke' Test -- When you plug it in, does it smoke and catch fire?

Smoke tests merely verify that the infrastructure is intact. Once
later tests are up, these become largely unnecessary, as later
function presumes successful import, etc.
"""

import nldi
import pytest
import sqlalchemy
from sqlalchemy.engine import URL as DB_URL


@pytest.mark.order(0)
@pytest.mark.unittest
def test_successful_import() -> None:
    """Does the module import at all?"""
    assert nldi.__version__ is not None


@pytest.mark.order(1)
@pytest.mark.unittest
def test_fixtures_present(runner) -> None:
    """Verify the CLI fixture is available."""
    assert runner is not None


@pytest.mark.order(2)
@pytest.mark.integration
def test_db_container_fixture(nldi_db_container) -> None:
    """Verify the database container fixture is available."""
    assert nldi_db_container["port"] == 5432
    assert nldi_db_container["dbname"] == "nldi"
    connection_str = DB_URL.create(
        "postgresql+psycopg2",
        username=nldi_db_container['user'],
        password=nldi_db_container['password'],
        host=nldi_db_container['host'],
        port=nldi_db_container['port'],
        database=nldi_db_container['dbname'],
    )
    engine = sqlalchemy.create_engine(connection_str)
    with engine.begin() as connection:
        (v,) = connection.execute(sqlalchemy.text("SELECT 1")).fetchone()
    assert v == 1
