# NLDI-py Onboarding Guide

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [Task](https://taskfile.dev/) (task runner)
- Docker (for integration tests)
- Access to the NLDI database credentials (GPG-encrypted at `~/.secrets/nldi.env.gpg`)

## First-Time Setup

```bash
# Clone and install
git clone <repo-url>
cd nldi-py
uv sync

# Verify the toolchain works
task check   # runs lint + format check + unit tests
```

## Running Locally

```bash
# Start the dev server (decrypts secrets, runs with --reload)
task dev

# The API is at http://localhost:8000/api/nldi
# Swagger docs at http://localhost:8000/api/nldi/docs
```

If you don't have the GPG-encrypted secrets file, you'll need the following env vars set manually:
`NLDI_DB_HOST`, `NLDI_DB_NAME`, `NLDI_DB_USERNAME`, `NLDI_DB_PASSWORD`, `PYGEOAPI_URL`.

## Project Layout

```
src/nldi/
├── asgi.py              # App factory — start here to understand wiring
├── config.py            # Env var configuration
├── middleware.py        # ASGI middleware (CORS, HEAD, disconnect, timing)
├── controllers/
│   ├── root.py          # Landing page, health, redirects
│   └── linked_data/     # All /linked-data/* endpoints
│       ├── __init__.py  # DI providers + shared helpers
│       ├── lookups.py   # Sources, features, position, hydrolocation
│       ├── navigation.py# Navigation flowlines + features
│       └── basin.py     # Drainage basin computation
├── db/
│   ├── __init__.py      # Engine + session provider
│   ├── models.py        # ORM table mappings (no logic)
│   ├── repos.py         # Repository classes (data access)
│   └── navigation.py    # Recursive CTE query builders
├── geojson.py           # GeoJSON structs + streaming serializer
├── jsonld.py            # JSON-LD builder
├── negotiate.py         # f= param validation + browser redirect
├── pygeoapi.py          # External service client
├── errors.py            # RFC 9457 error handlers
├── dto.py               # DataSource message struct
├── media.py             # MediaType enum
├── health.py            # Health check logic
└── util.py              # WKT parsing utility
```

## Common Tasks

| Command | What it does |
|---|---|
| `task test:unit` | Fast tests, no Docker, no network |
| `task test:integration` | Spins up PostGIS via testcontainers |
| `task test:parity` | Contract tests vs golden files (needs running app) |
| `task test:system` | Tests against live RDS (needs running app) |
| `task lint` | Ruff linter |
| `task format` | Auto-format with ruff |
| `task typecheck` | Type checking with ty |
| `task check` | Pre-commit gate: lint + format check + unit tests |
| `task dev` | Run app locally with hot reload |

## Development Workflow

1. **Unit tests drive development.** Write a failing test, make it pass, refactor. Unit tests are in `tests/unit/` and use fake repositories (see `tests/unit/conftest.py`).

2. **Integration tests validate SQL.** After a unit of work is complete, confirm queries work against real PostGIS. These use testcontainers with the `ghcr.io` database image.

3. **Parity tests prove compatibility.** Golden-file contract tests that compare Python responses to captured Java responses. Run these before declaring a feature "done."

## How to Add/Modify an Endpoint

1. Write unit tests in `tests/unit/` using the fake repos from `conftest.py`
2. Add or modify the route handler in the appropriate controller
3. If new data access is needed, add a method to the relevant repository
4. Run `task test:unit` until green
5. Run `task test:integration` to validate against real DB
6. Run `task check` before committing

## Key Conventions

- **No serialization in models.** ORM models map tables. GeoJSON/JSON-LD serialization is in `geojson.py` and `jsonld.py`.
- **One DB session per request.** Provided via DI, cleaned up automatically.
- **Explicit headers.** CORS, Cache-Control, Vary are set in middleware, not via framework config.
- **RFC 9457 errors.** All error responses are `application/problem+json` with type, title, status, detail.
- **Streaming for large results.** Navigation and feature-nav endpoints use `Stream` responses.
- **f= parameter.** Controls output format. Validated in `before_request` hook on controllers.

## Useful Entry Points for Reading

If you're trying to understand how a request flows:

1. `src/nldi/asgi.py` — see how the app is assembled
2. `src/nldi/middleware.py` — what happens before/after handlers
3. Pick any controller method — follow it from route to repository to response
4. `tests/unit/conftest.py` — see the fake repos to understand the data access contract

## Existing Documentation

- `docs/principles.md` — guiding design principles (read this first)
- `docs/dependencies.md` — what's used and why
- `docs/endpoint-outline.md` — full endpoint reference
- `docs/testing-strategy.md` — test layer philosophy
- `docs/tooling.md` — tools in use
- `docs/implementation-notes.md` — edge cases and decisions
