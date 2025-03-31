#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""
'Smoke' Test -- When you plug it in, does it smoke and catch fire?

Smoke tests merely verify that the infrastructure is intact. Once
later tests are up, these become largely unnecessary, as later
function presumes successful import, fixtures, etc.
"""

import psycopg
import pytest


def _make_db_connection_string(host: str, port: int, user: str, password: str, database: str) -> str:
    """
    Convenience fn to format connect info for low-level ``psycopg`` driver.

    We're using ``psycopg`` directly for healthcheck, rather than sqlalchemy -- as it is
    a shorter stack, with fewer sources of failure.
    """
    return f"dbname={database} user={user} host={host} port={port} password={password}"


@pytest.mark.order(0)
@pytest.mark.unittest
def test_successful_import() -> None:
    """Does the module import at all?"""
    from nldi import __version__

    assert __version__ is not None


# region: unit tests
@pytest.mark.order(1)
@pytest.mark.unittest
def test_runner_fixture_present(runner) -> None:
    """Verify the CLI fixture is available."""
    assert runner is not None


@pytest.mark.order(2)
@pytest.mark.unittest
def test_container_fixture_present(containerized_db_env_info) -> None:
    assert isinstance(containerized_db_env_info, dict)

    with psycopg.connect(  # << See note above about psycopg vs sqlalchemy
        _make_db_connection_string(
            host=containerized_db_env_info["NLDI_DB_HOST"],
            port=containerized_db_env_info["NLDI_DB_PORT"],
            user=containerized_db_env_info["NLDI_DB_USERNAME"],
            password=containerized_db_env_info["NLDI_DB_PASSWORD"],
            database=containerized_db_env_info["NLDI_DB_NAME"],
        )
    ) as conn:
        db_ping = conn.execute("SELECT 1").fetchone()
        success = bool(db_ping is not None and db_ping[0] == 1)
    assert success


# region: integration tests
@pytest.mark.order(2)
@pytest.mark.integration
def test_testdb_fixture_present(testdb_env_info) -> None:
    assert isinstance(testdb_env_info, dict)
    with psycopg.connect(  # << See note above about psycopg vs sqlalchemy
        _make_db_connection_string(
            host=testdb_env_info["NLDI_DB_HOST"],
            port=testdb_env_info["NLDI_DB_PORT"],
            user=testdb_env_info["NLDI_DB_USERNAME"],
            password=testdb_env_info["NLDI_DB_PASSWORD"],
            database=testdb_env_info["NLDI_DB_NAME"],
        )
    ) as conn:
        db_ping = conn.execute("SELECT 1").fetchone()
        success = bool(db_ping is not None and db_ping[0] == 1)
    assert success
