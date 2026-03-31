# Spec: PR 2.2 — GET /linked-data (list sources)

## Purpose

First real endpoint. Replaces the 501 stub with a working implementation that queries the database and returns the list of data sources. Also establishes the integration test infrastructure (testcontainers).

## API contract (parity with Java)

**Request:** `GET /linked-data`

**Response:** JSON array of source objects.

```json
[
  {
    "source": "comid",
    "sourceName": "NHDPlus comid",
    "features": "https://.../linked-data/comid"
  },
  {
    "source": "wqp",
    "sourceName": "Water Quality Portal",
    "features": "https://.../linked-data/wqp"
  }
]
```

**Notes:**
- `comid` is always included as a synthetic source (not in the DB) — appended by the application
- `features` URLs are fully qualified, built from `NLDI_BASE_URL` env var
- Response is `application/json`
- Sources come from the `crawler_source` table via `CrawlerSourceRepository`

## Config

New env var: `NLDI_BASE_URL` — the public-facing base URL (e.g. `https://api.water.usgs.gov/nldi`). Required for building `features` URLs. No default — fail if not set.

## DB config change

`get_database_url()` changes from expecting a single `NLDI_DATABASE_URL` to assembling from components:
- `NLDI_DB_HOST`
- `NLDI_DB_PORT` (default: 5432)
- `NLDI_DB_NAME`
- `NLDI_DB_USERNAME`
- `NLDI_DB_PASSWORD`

Assembled as: `postgresql+asyncpg://{user}:{pass}@{host}:{port}/{name}`

## Response shape (DTO)

A simple dataclass or msgspec struct:

```
source: str        — source_suffix from CrawlerSourceModel
sourceName: str    — source_name from CrawlerSourceModel
features: str      — fully qualified URL to the features endpoint
```

This is the message model — separate from the ORM model.

## DI wiring

`CrawlerSourceRepository` injected into the endpoint via Litestar DI, using the session from the advanced-alchemy plugin.

## Integration test infrastructure

- Testcontainers with `ghcr.io/internetofwater/nldi-db:demo`
- Session-scoped fixture: starts container, yields DB connection info, stops container
- Async engine + session fixtures for test use
- First integration test: `GET /linked-data` returns a non-empty list of sources with correct shape

## Unit tests

- `get_database_url()` assembles URL from component env vars
- `get_base_url()` required, raises if missing
- Response includes synthetic `comid` source
- Response shape matches contract

## What this PR does NOT include

- Other endpoints (2.3–2.7)
- JSON-LD support
- Pagination
