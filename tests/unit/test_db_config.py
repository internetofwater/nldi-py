import os

import pytest


def test_database_url_missing_raises():
    os.environ.pop("NLDI_DATABASE_URL", None)
    from nldi.config import get_database_url

    with pytest.raises(RuntimeError, match="NLDI_DATABASE_URL"):
        get_database_url()


def test_database_url_from_env(monkeypatch):
    monkeypatch.setenv("NLDI_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/nldi")
    from nldi.config import get_database_url

    assert get_database_url() == "postgresql+asyncpg://user:pass@localhost/nldi"
