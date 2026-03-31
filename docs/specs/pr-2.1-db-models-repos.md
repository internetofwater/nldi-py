# Spec: PR 2.1 — DB Setup, ORM Models, Repositories

## Purpose

Establish the data access layer: database connection, ORM models mapping to existing tables, and repository interfaces for simple lookups. This is the foundation for all Phase 2 endpoints.

## Database Connection

- SQLAlchemy async engine via `asyncpg`
- Connection string from env var: `NLDI_DATABASE_URL`
  - Format: `postgresql+asyncpg://user:pass@host:port/dbname`
  - No default — app should fail clearly if not set
- Engine config: `pool_pre_ping=True`, `pool_size=10`, `max_overflow=10`
- Session wired via Litestar DI (advanced-alchemy plugin or manual provider)

## ORM Models

Ported from pre-refactor. These map to existing database tables we don't control.

### nldi_data schema

| Model | Table | PK | Notes |
|---|---|---|---|
| `CrawlerSourceModel` | `crawler_source` | `crawler_source_id` | Source registry |
| `FeatureSourceModel` | `feature` | `identifier` | Features with geometry, FK to crawler_source and mainstem_lookup |
| `MainstemLookupModel` | `mainstem_lookup` | `nhdpv2_comid` | Mainstem URI lookup |

### nhdplus schema

| Model | Table | PK | Notes |
|---|---|---|---|
| `FlowlineModel` | `nhdflowline_np21` | `nhdplus_comid` | Flowlines with geometry |
| `FlowlineVAAModel` | `plusflowlinevaa_np21` | `comid` | Value-added attributes for navigation (Phase 3) |
| `CatchmentModel` | `catchmentsp` | `ogc_fid` | Catchment polygons |

### What changes from pre-refactor

- **Remove** `GeoJSONMixin` and `as_feature()` from models. Models are pure data/object layer — no serialization logic.
- **Remove** `__properties__()` — same reason.
- **Remove** `__geo_interface__` — geometry conversion moves to DTO or service layer.
- **Keep** association proxies on `FeatureSourceModel` and `FlowlineModel` (sourceName, source, mainstem) — these are object model concerns (navigating relationships), not message model.
- **Keep** `geomet` dependency only if needed for WKB parsing. Evaluate `ST_AsGeoJSON` as alternative (deferred decision from roadmap).

## Repositories

Using advanced-alchemy `SQLAlchemyAsyncRepository`. One per model that Phase 2 endpoints need.

| Repository | Model | Methods needed for Phase 2 |
|---|---|---|
| `CrawlerSourceRepository` | `CrawlerSourceModel` | `list()`, `get_one_or_none(suffix=...)` |
| `FeatureRepository` | `FeatureSourceModel` | `get_one_or_none(source, identifier)`, `list(source, limit, offset)` |
| `FlowlineRepository` | `FlowlineModel` | `get(comid)` |
| `CatchmentRepository` | `CatchmentModel` | `get_one_or_none(spatial intersect)` |

`FlowlineVAAModel` has no repo — it's only used in navigation CTEs (Phase 3).

## What this PR does NOT include

- DTOs / response serialization — that's per-endpoint in PRs 2.2–2.7
- GeoJSON conversion — deferred to endpoint PRs
- Navigation queries — Phase 3
- Service layer — repos are sufficient for simple lookups

## Dependencies added

- `advanced-alchemy`
- `sqlalchemy[asyncio]`
- `asyncpg`
- `geoalchemy2`
- `psycopg` / `psycopg-binary` (if needed by geoalchemy2)

## Acceptance criteria

- `uv sync` succeeds
- Models import cleanly
- Repos instantiate with a session
- Integration test: connect to testcontainers DB, verify a repo can query
- No serialization logic on models
