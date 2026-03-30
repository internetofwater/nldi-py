# NLDI-py Refactor Roadmap

Integration branch: `refactor/v3`
Reference snapshot: tag `pre-refactor`

## Phase 0: Project setup

Housekeeping before any feature work.

| PR | Description | Acceptance |
|---|---|---|
| 0.1 | Create `refactor/v3` branch, clean `src/` tree, `pyproject.toml` with updated deps (drop advanced-alchemy, Jinja2 tentatively) | `uv sync` succeeds, empty app |
| 0.2 | Taskfile with `lint`, `format`, `typecheck`, `test:unit`, `test:integration` tasks | All tasks runnable (tests pass trivially) |
| 0.3 | Migrate test scaffolding — `conftest.py`, testcontainers fixtures, pytest markers. Reorganize into `tests/unit/`, `tests/integration/`, `tests/parity/`, `tests/system/` | Existing DB fixtures work, markers filter correctly |

## Phase 1: Skeleton

All routes respond. Nothing touches the DB except health check.

| PR | Description | Depends on | Acceptance |
|---|---|---|---|
| 1.1 | App entry point, config loading, DB engine setup (plain SQLAlchemy async) | 0.1 | App starts, config loads from YAML |
| 1.2 | Middleware stack: CORS (unconditional), HEAD (fast-return), Cache-Control, Vary | 1.1 | Headers correct on every response (unit tests) |
| 1.3 | Error handling: RFC 9457 problem+json, exception handlers for 400/404/500/503/504 | 1.1 | Errors return `application/problem+json` with correct status codes |
| 1.4 | Content negotiation: `f=` validation (400 on invalid), browser redirect (`Accept: text/html` → click-here page) | 1.1 | Invalid `f=` rejected, browser redirect works |
| 1.5 | Route stubs: all endpoints defined, return 501. Health check functional. OpenAPI generation. | 1.1–1.4 | Every endpoint responds, OpenAPI spec matches expected paths |
| 1.6 | Legacy redirects: `/swagger-ui/index.html` → `/docs`, `/openapi` → `/docs` | 1.5 | Redirects return 301/302 to correct paths |

## Phase 2: Read-only lookups

One PR per endpoint or small logical group. Each PR includes integration tests against testcontainers.

| PR | Description | Depends on | Acceptance |
|---|---|---|---|
| 2.1 | ORM models (ported from pre-refactor, cleaned up). DTO definitions for response shapes. | 1.5 | Models map to DB tables, DTOs define wire format |
| 2.2 | `GET /linked-data` — list sources | 2.1 | Parity with Java response shape |
| 2.3 | `GET /linked-data/{source_name}` — list features by source | 2.1 | Parity, pagination works |
| 2.4 | `GET /linked-data/{source_name}/{identifier}` — single feature | 2.1 | Parity, 404 on missing |
| 2.5 | `GET /linked-data/comid/position` — flowline by spatial search | 2.1 | Parity, spatial query correct |
| 2.6 | `GET /linked-data/{source}/{id}/navigation` — nav modes | 2.1 | Returns correct mode URLs |
| 2.7 | `GET /linked-data/{source}/{id}/navigation/{nav_mode}` — nav info with mode validation | 2.1 | Parity, invalid mode returns 400 |

## Phase 3: Navigation

The heavy path. Port SQL queries from pre-refactor, apply resource discipline (one session, release before streaming).

| PR | Description | Depends on | Acceptance |
|---|---|---|---|
| 3.1 | Navigation query builder — CTE logic for UM, UT, DM, DD (ported from `NavigationService`) | 2.1 | Unit tests for query construction, integration tests for results |
| 3.2 | `GET .../navigation/{nav_mode}/flowlines` — flowline navigation | 3.1 | Parity, distance/trim/excludeGeometry params work |
| 3.3 | `GET .../navigation/{nav_mode}/{data_source}` — feature navigation | 3.1 | Parity, distance/excludeGeometry params work |

## Phase 4: External services

Endpoints that call pygeoapi. Proper timeout handling.

| PR | Description | Depends on | Acceptance |
|---|---|---|---|
| 4.1 | pygeoapi client (httpx) with timeout handling — distinct exception for timeouts → 504 | 1.3 | Unit tests with mocked responses, timeout returns 504 |
| 4.2 | `GET /linked-data/hydrolocation` | 4.1, 2.1 | Parity with Java |
| 4.3 | `GET /linked-data/{source}/{id}/basin` — including split catchment | 4.1, 2.1 | Parity, split catchment works, timeout → 504 |

## Phase 5: JSON-LD

| PR | Description | Depends on | Acceptance |
|---|---|---|---|
| 5.1 | `f=jsonld` support — evaluate build approach (Jinja vs Python builder), correct `application/ld+json` content type | 2.2–2.4, 3.2–3.3 | JSON-LD output matches expected graph structure |

## Open questions

Decisions to make during implementation, not before:

- **Repo strategy** — work on upstream repo (PRs are the permanent record in the right place, but visible to project owner) vs fork (private workflow, but PRs orphaned from upstream). Leaning upstream with a heads-up conversation.
- **msgspec** — keep for struct definitions + Litestar integration, or replace with DTOs entirely?
- **shapely** — can we eliminate direct usage (WKT parsing → regex, `to_shape()` → `ST_AsGeoJSON`)? GeoAlchemy2 transitive dep remains.
- **JSON-LD** — Jinja template or Python string builder? Decide in Phase 5 based on complexity.
- **`ST_AsGeoJSON` vs WKB** — benchmark DB-side GeoJSON conversion vs Python-side shapely conversion. Decide in Phase 2.
- **Content-Type** — `application/json` vs `application/vnd.geo+json` for GeoJSON endpoints. Java uses the latter. Match it?

## PR size guideline

Target: ~400 lines of non-test code per PR. If it's bigger, split it. Recalibrate as needed.
