# NLDI-py Refactor Strategy

> "A complex system that works is invariably found to have evolved from a simple system that worked." — John Gall

No big-bang rewrite. The system must be deployable and testable against the existing API contract at every
phase. Each phase produces a working system that does more than the last.

## Approach: Greenfield src, migrated tests

The pre-refactor codebase is tagged as `pre-refactor` for reference. The refactor starts with a clean `src/`
tree, applying the guiding principles from the start. The hard-won logic — SQL queries, navigation CTEs, ORM
model definitions — is copied in as needed, not rewritten.

What gets replaced: the plumbing (session management, serialization, middleware, DI wiring, Jinja templating).

What gets carried forward:

- SQLAlchemy ORM models (thin table mappings)
- Navigation query logic (recursive CTEs, distance calculations)
- Spatial query logic (PostGIS functions)
- Test suite (adapted to new structure, not discarded)
- Testcontainers setup and DB fixtures
- Test data (custom Docker image on ghcr.io)

## Phase 1: Skeleton

Stand up the application framework with every endpoint defined. All routes return the correct
path structure and content types. Endpoints that aren't yet implemented return `501 Not Implemented`.

This phase establishes:

- Application entry point and configuration
- Middleware (CORS, HEAD, Cache-Control, Vary — explicit, not framework-magic)
- Error handling (RFC 9457 problem+json)
- Content negotiation: the `f=` query parameter and browser detection redirect (no `f=` + `Accept: text/html` → "click here for JSON" page). This is a pre-request concern that applies to all endpoints.
- `f=` validation (reject invalid values with 400)
- Route definitions for all endpoints (see endpoint-outline.md)
- Database connection setup (plain SQLAlchemy async, no ORM wrappers)
- Health check (functional)

The test at this phase: every endpoint responds, content types are correct, headers are correct, errors are structured, browser redirect works. Nothing touches the database except health check.

## Phase 2: Read-only lookups (simple → complex)

Fill in endpoints that do straightforward database reads, starting with the simplest:

1. `GET /linked-data` — list sources
2. `GET /linked-data/{source_name}` — list features by source
3. `GET /linked-data/{source_name}/{identifier}` — single feature lookup
4. `GET /linked-data/comid/position` — flowline by spatial search
5. `GET /linked-data/{source_name}/{identifier}/navigation` — navigation modes
6. `GET /linked-data/{source_name}/{identifier}/navigation/{nav_mode}` — navigation info

Each endpoint is complete when it returns the same response body as the Java service for the same input.

## Phase 3: Navigation

The core complexity. Navigation queries (flowlines and features by nav mode) involve recursive CTEs and potentially large result sets.

1. `GET .../navigation/{nav_mode}/flowlines`
2. `GET .../navigation/{nav_mode}/{data_source}`

This phase also addresses trimming, distance defaults, and geometry exclusion.

## Phase 4: External service integration

Endpoints that depend on pygeoapi:

1. `GET /linked-data/hydrolocation`
2. `GET /linked-data/{source_name}/{identifier}/basin` (with split catchment)

This phase includes proper timeout handling (504, not 500).

## Phase 5: JSON-LD

Add `f=jsonld` support with correct `application/ld+json` content type. Evaluate whether
Jinja is needed for the JSON-LD graph structure or if a Python builder suffices.

## At every phase

- All existing endpoints continue to respond (501 if not yet implemented)
- Headers are correct (CORS, Cache-Control, Vary)
- Errors use RFC 9457
- One DB connection per request, released before response streaming
- Tests validate parity against known-good responses from the Java service
