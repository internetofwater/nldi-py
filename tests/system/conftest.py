"""System test fixtures."""

import os

import httpx
import pytest

BASE_URL = os.getenv("NLDI_TEST_URL", "http://localhost:8000/api/nldi")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL + "/", timeout=30) as c:
        yield c
