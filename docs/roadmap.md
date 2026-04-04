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

## Phase 3: Navigation ✅

| PR | Description | Status |
| --- | --- | --- |
| ~~3.1~~ | Navigation infrastructure + DM CTE, resolve comid, flowline nav handler | ✅ #172 |
| ~~3.2~~ | DD, UM, UT modes + navigation_query dispatcher | ✅ #173 |
| ~~3.3~~ | Feature navigation by data source | ✅ #174 |
| ~~3.4~~ | Trim start/tolerance on flowline navigation | ✅ #175 |
| ~~3.5~~ | excludeGeometry parameter on navigation endpoints | ✅ #176 |
| ~~3.6~~ | OpenAPI documentation polish pass | ✅ #177 |

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

- **JSON-LD** — Jinja template or Python string builder? Decide in Phase 5 based on complexity.

## Decided

- ~~**Repo strategy**~~ — working on upstream repo. PRs are the permanent record. ✅
- ~~**msgspec**~~ — keeping for struct definitions (GeoJSON DTOs, DataSource). Works well with Litestar serialization. ✅
- ~~**shapely**~~ — eliminated from geometry path via `GeoJSONGeometry` custom column type (#168). Still a transitive dep of GeoAlchemy2. Direct usage only remains for WKT parsing in pygeoapi service (Phase 4). ✅
- ~~**`ST_AsGeoJSON` vs WKB**~~ — `ST_AsGeoJSON` via custom column type. DB does the conversion. No shapely needed. ✅ #168
- ~~**Content-Type**~~ — `application/geo+json` (RFC 7946 standard). Java uses deprecated `application/vnd.geo+json`. ✅

## PR size guideline

Target: ~400 lines of non-test code per PR. If it's bigger, split it. Recalibrate as needed.
