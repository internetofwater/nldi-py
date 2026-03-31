"""Integration test fixtures — testcontainers with PostGIS."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


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

    dc.start()
    wait_for_logs(dc, "database system is ready to accept connections")

    client = dc.get_docker_client()
    host = client.bridge_ip(dc.get_wrapped_container().short_id)

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


@pytest.fixture(scope="session")
def db_engine(db_url):
    """Create async engine for integration tests."""
    engine = create_async_engine(db_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture()
async def db_session(db_engine):
    """Provide an async session for a single test."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
