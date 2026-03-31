import os

import pytest


def test_database_url_from_components(monkeypatch):
    monkeypatch.setenv("NLDI_DB_HOST", "dbhost")
    monkeypatch.setenv("NLDI_DB_PORT", "5433")
    monkeypatch.setenv("NLDI_DB_NAME", "mydb")
    monkeypatch.setenv("NLDI_DB_USERNAME", "user")
    monkeypatch.setenv("NLDI_DB_PASSWORD", "secret")
    from nldi.config import get_database_url

    assert get_database_url() == "postgresql+asyncpg://user:secret@dbhost:5433/mydb"


def test_database_url_default_port(monkeypatch):
    monkeypatch.setenv("NLDI_DB_HOST", "dbhost")
    monkeypatch.setenv("NLDI_DB_NAME", "mydb")
    monkeypatch.setenv("NLDI_DB_USERNAME", "user")
    monkeypatch.setenv("NLDI_DB_PASSWORD", "secret")
    monkeypatch.delenv("NLDI_DB_PORT", raising=False)
    from nldi.config import get_database_url

    assert "5432" in get_database_url()


def test_database_url_missing_host_raises(monkeypatch):
    monkeypatch.delenv("NLDI_DB_HOST", raising=False)
    monkeypatch.setenv("NLDI_DB_NAME", "mydb")
    monkeypatch.setenv("NLDI_DB_USERNAME", "user")
    monkeypatch.setenv("NLDI_DB_PASSWORD", "secret")
    from nldi.config import get_database_url

    with pytest.raises(RuntimeError):
        get_database_url()


def test_base_url_from_env(monkeypatch):
    monkeypatch.setenv("NLDI_BASE_URL", "https://api.water.usgs.gov/nldi")
    from nldi.config import get_base_url

    assert get_base_url() == "https://api.water.usgs.gov/nldi"


def test_base_url_missing_raises(monkeypatch):
    monkeypatch.delenv("NLDI_BASE_URL", raising=False)
    from nldi.config import get_base_url

    with pytest.raises(RuntimeError, match="NLDI_BASE_URL"):
        get_base_url()
