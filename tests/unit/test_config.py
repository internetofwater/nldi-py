import os

from nldi.config import get_log_level, get_prefix


def test_default_prefix():
    os.environ.pop("NLDI_PREFIX", None)
    assert get_prefix() == "/api/nldi"


def test_custom_prefix(monkeypatch):
    monkeypatch.setenv("NLDI_PREFIX", "/custom")
    assert get_prefix() == "/custom"


def test_default_log_level():
    os.environ.pop("NLDI_LOG_LEVEL", None)
    import logging

    assert get_log_level() == logging.WARNING


def test_custom_log_level(monkeypatch):
    import logging

    monkeypatch.setenv("NLDI_LOG_LEVEL", "DEBUG")
    assert get_log_level() == logging.DEBUG


def test_invalid_log_level_falls_back(monkeypatch):
    import logging

    monkeypatch.setenv("NLDI_LOG_LEVEL", "NONSENSE")
    assert get_log_level() == logging.WARNING
