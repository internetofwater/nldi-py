"""Integration test fixtures — testcontainers with PostGIS."""

import logging
import time

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.core.container import DockerContainer

logger = logging.getLogger(__name__)


def _wait_for_db(host: str, port: int, user: str, password: str, dbname: str, timeout: int = 120) -> None:
    """Retry until the database has the expected schema ready."""
    import asyncio

    async def _try_query():
        conn = await asyncpg.connect(host=host, port=port, user=user, password=password, database=dbname)
        try:
            await conn.fetch("SELECT 1 FROM nldi_data.crawler_source LIMIT 1")
        finally:
            await conn.close()

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            asyncio.run(_try_query())
            logger.info("Database schema is ready.")
            return
        except Exception as e:
            logger.debug("Waiting for DB: %s", e)
            time.sleep(2)
    raise TimeoutError(f"Database schema not ready after {timeout}s")


@pytest.fixture(scope="session")
def nldi_db_container():
    """Start the NLDI PostGIS container for integration tests."""
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
    dc.with_volume_mapping("nldi-test-data", "/var/lib/postgresql/data", mode="rw")

    dc.start()

    client = dc.get_docker_client()
    host = client.bridge_ip(dc.get_wrapped_container().short_id)

    _wait_for_db(host=host, port=5432, user="nldi", password="changeMe", dbname="nldi")

    yield {
        "host": host,
        "port": "5432",
        "name": "nldi",
        "user": "nldi",
        "password": "changeMe",
    }

    dc.stop()


@pytest.fixture(scope="session")
def db_url(nldi_db_container):
    """Build async database URL from container info."""
    c = nldi_db_container
    return f"postgresql+asyncpg://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['name']}"


@pytest.fixture()
async def db_session(db_url):
    """Provide an async session for a single test."""
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
def app_client(db_url):
    """Provide a TestClient wired to the real containerized DB."""
    import os

    from litestar.testing import TestClient

    from nldi.asgi import create_app

    # Point engine at the test container
    os.environ["NLDI_DB_HOST"] = "unused"  # get_engine won't be called — we override
    import nldi.db as db_mod

    db_mod._engine = create_async_engine(db_url, pool_pre_ping=True)

    app = create_app()
    with TestClient(app=app) as client:
        yield client

    # Reset engine singleton
    db_mod._engine = None
