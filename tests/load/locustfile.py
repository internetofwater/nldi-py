"""Locust load test for NLDI API.

Scenarios weighted toward navigation (the heavy path).
Uses the Colorado River worklist for random comid selection.

Usage:
    task test:load                          # headless, 20 users, 2 min
    uv run locust -f tests/load/locustfile.py  # web UI at localhost:8089

Target host defaults to http://localhost:8000/api/nldi (override with --host).
"""

import random
from pathlib import Path

from locust import HttpUser, between, task

WORKLIST = Path(__file__).parent / "worklist.txt"
COMIDS = [line.strip() for line in WORKLIST.read_text().splitlines() if line.strip()]


class NLDIUser(HttpUser):
    """Simulated NLDI user with realistic traffic mix."""

    wait_time = between(0.5, 2)

    # --- Navigation: heavy path, highest weight ---

    @task(5)
    def nav_dm_flowlines(self):
        """DM flowline navigation — the most expensive query."""
        comid = random.choice(COMIDS)  # noqa: S311
        self.client.get(
            f"/linked-data/comid/{comid}/navigation/DM/flowlines?distance=50&f=json",
            name="/navigation/DM/flowlines",
        )

    @task(3)
    def nav_um_flowlines(self):
        """UM flowline navigation."""
        comid = random.choice(COMIDS)  # noqa: S311
        self.client.get(
            f"/linked-data/comid/{comid}/navigation/UM/flowlines?distance=50&f=json",
            name="/navigation/UM/flowlines",
        )

    @task(2)
    def nav_dm_features(self):
        """DM feature navigation — joins to crawler sources."""
        comid = random.choice(COMIDS)  # noqa: S311
        self.client.get(
            f"/linked-data/comid/{comid}/navigation/DM/nwissite?distance=50&f=json",
            name="/navigation/DM/features",
        )

    # --- Single lookups: baseline, should stay fast ---

    @task(3)
    def single_feature(self):
        """Single feature lookup."""
        comid = random.choice(COMIDS)  # noqa: S311
        self.client.get(
            f"/linked-data/comid/{comid}?f=json",
            name="/comid/{id}",
        )

    @task(1)
    def source_list(self):
        """Source list — lightest endpoint."""
        self.client.get("/linked-data?f=json", name="/linked-data")

    # --- Basin: exercises DB + potentially pygeoapi ---

    @task(1)
    def basin(self):
        """Basin query."""
        comid = random.choice(COMIDS)  # noqa: S311
        self.client.get(
            f"/linked-data/comid/{comid}/basin?f=json",
            name="/basin",
        )
