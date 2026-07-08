# NLDI-py Architecture Overview

## What is NLDI?

The Network Linked Data Index (NLDI) is a REST API that sits in front of the National Hydrography Dataset (NHDPlus v2.1). It lets clients discover hydrologic features, navigate the stream network upstream/downstream, compute drainage basins, and find linked data sources (water quality sites, stream gauges, etc.) along navigation paths.

This Python implementation is a drop-in replacement for the original Java/Spring Boot service. It preserves the same endpoints, response shapes, and status codes — existing clients work unchanged.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Uvicorn (ASGI server, multi-worker)                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Litestar Application                                     │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  Middleware Stack                                    │  │  │
│  │  │  • headers_middleware (CORS, Cache-Control, Vary)    │  │  │
│  │  │  • head_shortcircuit (skip DB for HEAD on heavy)     │  │  │
│  │  │  • disconnect_guard (cancel queries on hangup)       │  │  │
│  │  │  • timing_middleware (request logging + correlation) │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  Controllers                                         │  │  │
│  │  │  • RootController (landing, health, docs)            │  │  │
│  │  │  • LookupController (sources, features, position)    │  │  │
│  │  │  • NavigationController (flowlines, features by nav) │  │  │
│  │  │  • BasinController (drainage basin polygon)          │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  Data Layer                                          │  │  │
│  │  │  • Repositories (thin wrappers on SQLAlchemy async)  │  │  │
│  │  │  • Navigation CTEs (recursive SQL for network walk)  │  │  │
│  │  │  • ORM Models (table mappings, no business logic)    │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────┐            ┌─────────────────────┐
│  PostgreSQL/PostGIS  │            │  pygeoapi (external) │
│  NHDPlus v2.1 data   │            │  flowtrace, split    │
│  3 schemas:          │            │  catchment services  │
│  • nldi_data         │            └─────────────────────┘
│  • nhdplus           │
│  • characteristic_data│
└─────────────────────┘
```

## Layer Responsibilities

### Controllers (`src/nldi/controllers/`)

HTTP interface. Each controller is a Litestar `Controller` class with route handlers. Controllers:
- Validate input (query params, path params)
- Call repositories to fetch data
- Build response objects (GeoJSON Features, navigation URLs)
- Return `Response` or `Stream` with appropriate media type

Controllers do not contain SQL or know about table structure.

### Repositories (`src/nldi/db/repos.py`)

Data access boundary. Four repository classes, all inheriting from `AsyncRepository`:

| Repository | Responsibility |
|---|---|
| `CrawlerSourceRepository` | Source registry lookups (what data sources exist) |
| `FeatureRepository` | Feature lookups, list by source, navigation-joined features |
| `FlowlineRepository` | Flowline lookups, navigation-joined flowlines, measure/reachcode computation |
| `CatchmentRepository` | Spatial point-in-polygon, basin geometry aggregation |

Repositories own the SQLAlchemy session and expose domain-oriented methods. They also support query cancellation via `cancel_running_query()` for client disconnect handling.

### Navigation Queries (`src/nldi/db/navigation.py`)

Recursive CTEs that walk the NHDPlus network graph. Four modes:
- **DM** — Downstream Main (follow main channel)
- **DD** — Downstream with Diversions (follow all downstream paths)
- **UM** — Upstream Main (follow main channel upstream)
- **UT** — Upstream with Tributaries (follow all upstream paths)

Each function returns a `sqlalchemy.Select` producing a list of COMIDs. The caller joins this to flowlines or features to produce results.

### ORM Models (`src/nldi/db/models.py`)

Pure table mappings across three database schemas:
- `nldi_data` — crawler sources, features, mainstem lookups
- `nhdplus` — flowlines, flowline VAA (routing attributes), catchments
- `characteristic_data` — optimized copies of catchments and VAA for basin queries

Models have no serialization logic. The `GeoJSONGeometry` column type auto-wraps selects in `ST_AsGeoJSON()`.

### Message Layer

Serialization is handled separately from models:
- `geojson.py` — msgspec structs for GeoJSON (Feature, FeatureCollection, geometry types) + streaming serializer
- `jsonld.py` — JSON-LD builder using schema.org/hydrologic features vocabularies
- `dto.py` — DataSource struct for the source list endpoint

### Middleware (`src/nldi/middleware.py`)

Four ASGI middleware functions, applied at different router levels:

| Middleware | Scope | Purpose |
|---|---|---|
| `headers_middleware_factory` | App-wide | Unconditional CORS, Cache-Control, Vary headers |
| `head_shortcircuit_factory` | App-wide | Skip handler body for HEAD on DB-heavy endpoints |
| `disconnect_guard_factory` | Linked-data router | Cancel in-flight DB queries on client disconnect |
| `timing_middleware_factory` | Linked-data router | Request timing + correlation ID logging |

### External Service Client (`src/nldi/pygeoapi.py`)

Async HTTP client for pygeoapi (flowtrace and split-catchment services). Distinct exception types (`PyGeoAPIError`, `PyGeoAPITimeoutError`) map to 502/504 responses.

## Key Design Patterns

### Dependency Injection

Litestar's DI system provides repositories and the pygeoapi client to handlers. Providers are defined in `controllers/linked_data/__init__.py`. This enables easy test substitution — unit tests inject fakes without touching the DB.

### Client Disconnect Cancellation

The `disconnect_guard` middleware monitors the ASGI receive channel. On disconnect:
1. Calls `cancel_running_query()` on registered repos
2. For navigation queries: `pg_cancel_backend()` (fast, connection reusable)
3. For basin queries: closes the TCP connection (GEOS ops ignore cancel signals)

### Streaming Responses

Large navigation results are streamed as chunked GeoJSON. The DB query completes first (connection released), then bytes are yielded incrementally. A client hangup mid-stream has no pool impact.

### Content Negotiation

The `f=` query parameter controls output format (`json`, `jsonld`, `html`). Browser requests (Accept: text/html) without `f=` get a redirect page pointing to the JSON version.

## Database Schema

The application is read-only against a shared PostGIS database populated by a separate crawler process. Three schemas:

- **nldi_data** — `crawler_source` (source registry), `feature` (indexed features), `mainstem_lookup`
- **nhdplus** — `nhdflowline_np21` (stream geometries), `plusflowlinevaa_np21` (routing topology), `catchmentsp` (local drainage polygons)
- **characteristic_data** — `plusflowlinevaa_np21` and `catchmentsp` (optimized copies with better indexing for basin traversal)

## Configuration

All configuration is via environment variables (see `src/nldi/config.py`):

| Variable | Purpose | Default |
|---|---|---|
| `NLDI_DB_HOST`, `NLDI_DB_NAME`, `NLDI_DB_USERNAME`, `NLDI_DB_PASSWORD` | Database connection (required) | — |
| `NLDI_DB_PORT` | Database port | `5432` |
| `NLDI_URL` | Public-facing base URL | `http://localhost:8000` |
| `NLDI_PATH` | URL path prefix | `/api/nldi` |
| `NLDI_LOG_LEVEL` | Log level | `WARNING` |
| `PYGEOAPI_URL` | pygeoapi service URL | — |
| `springFrameworkLogLevel` | Legacy log level (fallback) | — |

## Error Handling

All errors return RFC 9457 Problem Details (`application/problem+json`). Specific status codes:
- 400 — invalid parameters (with detail explaining valid options)
- 404 — resource not found (with what was looked for)
- 502 — pygeoapi upstream error (surfaces upstream detail)
- 503 — database unavailable
- 504 — pygeoapi timeout
- 500 — unhandled (reference ID for log correlation, no internal details leaked)
