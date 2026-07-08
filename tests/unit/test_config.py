"""Unit tests for configuration."""

import os

import pytest

from nldi.config import get_base_url, get_database_url, get_log_level, get_prefix


class TestPrefix:
    def test_default(self):
        os.environ.pop("NLDI_PATH", None)
        assert get_prefix() == "/api/nldi"

    def test_custom(self, monkeypatch):
        monkeypatch.setenv("NLDI_PATH", "/custom")
        assert get_prefix() == "/custom"


class TestLogLevel:
    def test_default(self):
        os.environ.pop("NLDI_LOG_LEVEL", None)
        assert get_log_level() == "WARNING"

    def test_custom(self, monkeypatch):
        monkeypatch.setenv("NLDI_LOG_LEVEL", "DEBUG")
        assert get_log_level() == "DEBUG"

    def test_invalid_falls_back(self, monkeypatch):
        monkeypatch.setenv("NLDI_LOG_LEVEL", "NONSENSE")
        assert get_log_level() == "WARNING"


class TestDatabaseUrl:
    def test_from_components(self, monkeypatch):
        monkeypatch.setenv("NLDI_DB_HOST", "dbhost")
        monkeypatch.setenv("NLDI_DB_PORT", "5433")
        monkeypatch.setenv("NLDI_DB_NAME", "mydb")
        monkeypatch.setenv("NLDI_DB_USERNAME", "user")
        monkeypatch.setenv("NLDI_DB_PASSWORD", "secret")
        assert get_database_url() == "postgresql+psycopg://user:secret@dbhost:5433/mydb"

    def test_default_port(self, monkeypatch):
        monkeypatch.setenv("NLDI_DB_HOST", "dbhost")
        monkeypatch.setenv("NLDI_DB_NAME", "mydb")
        monkeypatch.setenv("NLDI_DB_USERNAME", "user")
        monkeypatch.setenv("NLDI_DB_PASSWORD", "secret")
        monkeypatch.delenv("NLDI_DB_PORT", raising=False)
        assert "5432" in get_database_url()

    def test_missing_host_raises(self, monkeypatch):
        monkeypatch.delenv("NLDI_DB_HOST", raising=False)
        monkeypatch.setenv("NLDI_DB_NAME", "mydb")
        monkeypatch.setenv("NLDI_DB_USERNAME", "user")
        monkeypatch.setenv("NLDI_DB_PASSWORD", "secret")
        with pytest.raises(RuntimeError):
            get_database_url()


class TestBaseUrl:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("NLDI_URL", "https://api.water.usgs.gov")
        monkeypatch.setenv("NLDI_PATH", "/nldi")
        assert get_base_url() == "https://api.water.usgs.gov/nldi"

    def test_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("NLDI_URL", "https://api.water.usgs.gov/")
        monkeypatch.setenv("NLDI_PATH", "/nldi")
        assert get_base_url() == "https://api.water.usgs.gov/nldi"

    def test_falls_back_to_localhost(self, monkeypatch):
        monkeypatch.delenv("NLDI_URL", raising=False)
        monkeypatch.delenv("NLDI_PATH", raising=False)
        assert get_base_url() == "http://localhost:8000/api/nldi"
