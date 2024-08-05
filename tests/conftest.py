#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#
"""Configuration for running pytest"""

import logging
import pathlib

import pytest
import sqlalchemy
from click.testing import CliRunner
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


@pytest.fixture
def runner():
    """Runner for cli-related tests."""
    return CliRunner()


@pytest.fixture(scope="session")
def nldi_db_container():
    """Database connection for NLDI database."""
    dc = DockerContainer("ghcr.io/internetofwater/nldi-db:demo")
    dc.with_exposed_ports(5432)
    dc.with_env("POSTGRES_PASSWORD", "changeMe")
    dc.with_env("NLDI_DATABASE_ADDRESS", "localhost")
    dc.with_env("NLDI_DATABASE_NAME", "nldi")
    dc.with_env("NLDI_DB_OWNER_USERNAME", "nldi")
    dc.with_env("NLDI_DB_OWNER_PASSWORD", "changeMe")
    dc.with_env("NLDI_SCHEMA_OWNER_USERNAME", "nldi_schema_owner")
    dc.with_env("NLDI_SCHEMA_OWNER_PASSWORD", "changeMe")
    dc.with_env("NHDPLUS_SCHEMA_OWNER_USERNAME", "nhdplus")
    dc.with_env("NLDI_READ_ONLY_USERNAME", "read_only_user")
    dc.with_env("NLDI_READ_ONLY_PASSWORD", "changeMe")
    dc.with_volume_mapping("data", "/var/lib/postgresql/data", mode="rw")

    dc.start()
    delay = wait_for_logs(dc, "database system is ready to accept connections")
    logging.info(f"Postgres container started in {delay} seconds")

    client = dc.get_docker_client()
    db_info = {
        "user": "nldi",
        "password": "changeMe",
        "host": client.bridge_ip(dc.get_wrapped_container().short_id),
        "port": 5432,
        "dbname": "nldi",
    }
    yield db_info

    dc.stop()

@pytest.fixture(scope="session")
def config_yaml():
    """Configuration file for tests."""
    here = pathlib.Path(__file__).parent
    return here / "data" / "sources_config.yml"
