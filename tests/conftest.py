#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0-1.0
#
"""Configuration for running pytest"""

import pathlib
from collections.abc import Generator

import pytest
from click.testing import CliRunner
from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL as DB_URL
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


@pytest.fixture
def runner():
    """Runner for cli-related tests."""
    # TODO: We currently don't have any CLI functions or capabilities defined. A future enhancement is
    # to put the crawler into this repo, which is a CLI.
    return CliRunner()


@pytest.fixture(scope="session")
def yaml_config_file() -> pathlib.Path:
    """Sample configuration file for tests."""
    # TODO: should this be hard-coded to specific location?  Is there a better place for it?
    here = pathlib.Path(__file__).parent.resolve()
    _f = here / "data" / "nldi_server_config.yml"
    return _f


@pytest.fixture(scope="session")
def localhost_env_info() -> dict[str, str]:
    """
    Update environment variables for tests.

    The current YAML parser will substitute environment variables in the
    configuration file. If an undefined variable is encountered, it will
    fill that value with a NoData value.

    These values are not especially meaningful -- but provide defaults suitable
    for testing the loading of the config file.

    """
    return dict(
        NLDI_URL="https://localhost/",
        NLDI_PATH="/api/nldi",
        NLDI_DB_HOST="localhost",
        NLDI_DB_PORT=5432,
        NLDI_DB_NAME="nldi",
        NLDI_DB_USERNAME="nldi",
        NLDI_DB_PASSWORD="changeMe",
    )


@pytest.fixture(scope="session")
def containerized_db_env_info():
    """
    Database connection for NLDI database.

    This fixture will start a Docker container with a Postgres database
    from the named container image. That image depends on various
    environment variables to configure the database as part of its boot
    sequence. These are all defined using ``.with_env()`` calls here before
    the container is started.

    """
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
    # ^^^^^^^^^^^^^^^ This volume mapping is important -- it will allow the container to persist
    # its database between invocations.  Without a means of persisting the database, the container
    # will have to re-initialize from scratch with each container start.

    dc.start()
    delay = wait_for_logs(dc, "database system is ready to accept connections")

    client = dc.get_docker_client()

    db_info = dict(
        NLDI_URL="https://localhost/",
        NLDI_PATH="/api/nldi",
        NLDI_DB_HOST=client.bridge_ip(dc.get_wrapped_container().short_id),
        NLDI_DB_PORT=5432,
        NLDI_DB_NAME="nldi",
        NLDI_DB_USERNAME="nldi",
        NLDI_DB_PASSWORD="changeMe",
    )

    yield db_info

    dc.stop()


@pytest.fixture()
def testdb_env_info() -> dict[str, str]:
    """
    Loads environment variables from the .env

    Note that this file must exist in a specific location and contain the correct information.

    DO NOT !!! commit the env file to the repository.
    """
    return dotenv_values(pathlib.Path(__file__).parent / "data" / "secret.env")


@pytest.fixture()
def engine_testdb(testdb_env_info) -> Generator[Engine, None, None]:
    """A sqlalchemy engine, configured for the containerized db."""
    _URL = DB_URL.create(  # noqa: N806
        "postgresql+psycopg",
        username=testdb_env_info["NLDI_DB_USERNAME"],
        password=testdb_env_info["NLDI_DB_PASSWORD"],
        host=testdb_env_info["NLDI_DB_HOST"],
        port=testdb_env_info["NLDI_DB_PORT"],
        database=testdb_env_info["NLDI_DB_NAME"],
    )
    _private_engine = create_engine(_URL, echo=True)
    try:
        yield _private_engine
    finally:
        _private_engine.dispose()


@pytest.fixture()
def dbsession_testdb(engine_testdb) -> Generator[Session, None, None]:
    """A sqlalchemy session, connecting to the containerized DB."""
    session = sessionmaker(bind=engine_testdb, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def engine_containerized(containerized_db_env_info) -> Generator[Engine, None, None]:
    """A sqlalchemy engine, configured for the containerized db."""
    _URL = DB_URL.create(  # noqa: N806
        "postgresql+psycopg",
        username=containerized_db_env_info["NLDI_DB_USERNAME"],
        password=containerized_db_env_info["NLDI_DB_PASSWORD"],
        host=containerized_db_env_info["NLDI_DB_HOST"],
        port=containerized_db_env_info["NLDI_DB_PORT"],
        database=containerized_db_env_info["NLDI_DB_NAME"],
    )
    _private_engine = create_engine(_URL, echo=True)
    try:
        yield _private_engine
    finally:
        _private_engine.dispose()


@pytest.fixture()
def dbsession_containerized(engine_containerized) -> Generator[Session, None, None]:
    """A sqlalchemy session, connecting to the containerized DB."""
    session = sessionmaker(bind=engine_containerized, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def f_client_containerized(monkeypatch, yaml_config_file, containerized_db_env_info):
    """
    A Flask-connected client, configured to use the containerized testing database.

    The containerized database is intended for integration testing: testing at the API endpoint
    level and all business logic that it invokes.
    """
    for k, v in containerized_db_env_info.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("NLDI_CONFIG", yaml_config_file)
    from nldi.wsgi import flask_nldi_app_factory

    _app = flask_nldi_app_factory()
    with _app.test_client() as client:
        yield client


@pytest.fixture()
def f_client_testdb(monkeypatch, yaml_config_file, testdb_env_info):
    """
    A Flask-connected client, configured to use the cloud-hosted testing database.

    This database connection is intended for system/end-to-end testing and performance
    testing. The main difference between this and the containerized database connection
    is the volume of data in the database, and that it requires a network connection
    to the AWS-hosted database (rather than a containerized extract of that database).
    """
    for k, v in testdb_env_info.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("NLDI_CONFIG", yaml_config_file)
    from nldi.wsgi import flask_nldi_app_factory

    _app = flask_nldi_app_factory()
    with _app.test_client() as client:
        yield client
