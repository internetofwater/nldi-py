# NLDI-py Refactor Roadmap

Integration branch: `refactor/v3`
Reference snapshot: tag `pre-refactor`

## Phase 0: Project setup ✅

Housekeeping before any feature work.

| PR | Description | Status |
| --- | --- | --- |
| ~~0.1~~ | Clean `src/` tree, `pyproject.toml` with minimal deps | ✅ #156 |
| ~~0.2~~ | Taskfile + test reorganization (combined 0.2 and 0.3) | ✅ #157 |

## Phase 1: Skeleton ✅

All routes respond. Nothing touches the DB.

| PR | Description | Status |
| --- | --- | --- |
| ~~1.1~~ | App entry point, config via env vars, Litestar app shell | ✅ #158 |
| ~~1.2~~ | Middleware: CORS (unconditional), Cache-Control, Vary | ✅ #159 |
| ~~1.3~~ | Error handling: RFC 9457 problem+json with error reference IDs | ✅ #160 |
| ~~1.4~~ | Content negotiation: `f=` validation, browser redirect, MediaType enum | ✅ #161 |
| ~~1.5~~ | Route stubs (501), health check, HEAD via `@head` multi-path, wiring | ✅ #162 |
| ~~1.6~~ | Legacy redirects: `/swagger-ui/index.html` → `/docs`, `/openapi` → `/docs` | ✅ #163 |

## Phase 2: Read-only lookups ✅

One PR per endpoint or small logical group. Each PR includes integration tests against testcontainers.

| PR | Description | Status |
| --- | --- | --- |
| ~~2.1~~ | DB engine setup, ORM models, repos, type checking | ✅ #164 |
| ~~2.2~~ | `GET /linked-data` — list sources, integration test infra, fake repos, DTOs | ✅ #165 |
| ~~2.3~~ | `GET /linked-data/{source_name}/{identifier}` — single feature (GeoJSON pattern) | ✅ #166 |
| ~~2.4~~ | `GET /linked-data/{source_name}` — list features by source + pagination | ✅ #167 |
| ~~geo~~ | Geometry serialization via GeoJSONGeometry custom column type | ✅ #168 |
| ~~2.5~~ | `GET /linked-data/comid/position` — flowline by spatial search | ✅ #169 |
| ~~2.6+2.7~~ | Navigation modes + navigation info with mode validation | ✅ #170 |

## Phase 3: Navigation

The heavy path. Port SQL queries from pre-refactor, apply resource discipline (one session, release before streaming).

| PR | Description | Depends on | Acceptance |
| --- | --- | --- | --- |
| 3.1 | Navigation query builder — CTE logic for UM, UT, DM, DD (ported from `NavigationService`) | 2.1 | Unit tests for query construction, integration tests for results |
| 3.2 | `GET .../navigation/{nav_mode}/flowlines` — flowline navigation | 3.1 | Parity, distance/trim/excludeGeometry params work |
| 3.3 | `GET .../navigation/{nav_mode}/{data_source}` — feature navigation | 3.1 | Parity, distance/excludeGeometry params work |

## Phase 4: External services

Endpoints that call pygeoapi. Proper timeout handling.

| PR | Description | Depends on | Acceptance |
| --- | --- | --- | --- |
| 4.1 | pygeoapi client (httpx) with timeout handling — distinct exception for timeouts → 504 | 1.3 | Unit tests with mocked responses, timeout returns 504 |
| 4.2 | `GET /linked-data/hydrolocation` | 4.1, 2.1 | Parity with Java |
| 4.3 | `GET /linked-data/{source}/{id}/basin` — including split catchment | 4.1, 2.1 | Parity, split catchment works, timeout → 504 |

## Phase 5: JSON-LD

| PR | Description | Depends on | Acceptance |
| --- | --- | --- | --- |
| 5.1 | `f=jsonld` support — evaluate build approach (Jinja vs Python builder), correct `application/ld+json` content type | 2.2–2.4, 3.2–3.3 | JSON-LD output matches expected graph structure |

## Open questions

Decisions to make during implementation, not before:

- **Repo strategy** — working on upstream repo. PRs are the permanent record in the right place.
- **msgspec** — keep for struct definitions + Litestar integration, or replace with DTOs entirely?
- **shapely** — can we eliminate direct usage (WKT parsing → regex, `to_shape()` → `ST_AsGeoJSON`)? GeoAlchemy2 transitive dep remains.
- **JSON-LD** — Jinja template or Python string builder? Decide in Phase 5 based on complexity.
- **`ST_AsGeoJSON` vs WKB** — benchmark DB-side GeoJSON conversion vs Python-side shapely conversion. Decide in Phase 2.
- **Content-Type** — `application/json` vs `application/vnd.geo+json` for GeoJSON endpoints. Java uses the latter. Match it?

## PR size guideline

Target: ~400 lines of non-test code per PR. If it's bigger, split it. Recalibrate as needed.
