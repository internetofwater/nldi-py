# NLDI-py Decision Log

Significant technical decisions made during the Java-to-Python refactor. Each entry captures what was decided, why, and what alternatives were considered.

---

## 1. Litestar over Flask (and FastAPI)

**Decision:** Replace Flask with Litestar as the ASGI framework.

**Why Flask was not viable:**

- **Sync-only (WSGI).** Flask ties up a worker thread for the entire request. Navigation queries can take seconds — under load, threads exhaust quickly. Litestar is ASGI (async-native), so a single worker handles many concurrent I/O-bound requests without blocking.
- **No native async database support.** SQLAlchemy's async engine (`AsyncSession`, `create_async_engine`) requires an async framework. With Flask you'd need workarounds like running the event loop manually or bolting async on top of WSGI — fragile and defeating the purpose.
- **Client disconnect cancellation is impossible.** The disconnect-guard middleware (cancel in-flight DB queries when a client hangs up) relies on monitoring the ASGI `receive` channel for `http.disconnect`. WSGI has no equivalent mechanism.
- **Streaming is limited.** Flask can stream via generators, but it's still bound by WSGI's synchronous model. ASGI streaming with chunked transfer is more natural and doesn't hold a worker thread for the duration.
- **No built-in DI.** Flask has no dependency injection system. Litestar's DI maps directly to the repository pattern and makes test substitution trivial (inject fakes without touching the DB).
- **HEAD handling requires manual work.** Flask doesn't automatically handle HEAD for routes. Litestar handles it natively, and our middleware can selectively short-circuit heavy endpoints.
- **Connection pool pressure.** With sync Flask + Gunicorn, you need one DB connection per worker thread for the full request duration. With async, a connection is held only during actual query execution — the same pool serves far more concurrent requests.

**Why Litestar over FastAPI:**

- Litestar provides DI, DTO validation, and OpenAPI generation without requiring Pydantic.
- Its DI system is more flexible for testing than FastAPI's `Depends`.
- Controller classes group related endpoints naturally.

**Alternatives considered:**
- FastAPI — more popular, but Pydantic dependency adds weight and its DI is less flexible.
- Starlette bare — too low-level; would require reimplementing routing, DI, and OpenAPI from scratch.

---

## 2. msgspec over Pydantic for serialization

**Decision:** Use msgspec Structs for GeoJSON and DTO definitions.

**Why:** msgspec is significantly faster for serialization/deserialization and integrates well with Litestar. GeoJSON responses can be large (thousands of features); serialization speed matters. Structs are also simpler — plain data containers without validation magic.

**Alternatives considered:**
- Pydantic — heavier, slower for our use case (we validate at the boundary, not in the model layer).
- dataclasses + manual JSON — more boilerplate, no streaming support.

---

## 3. Removed advanced-alchemy

**Decision:** Replace advanced-alchemy with a minimal `AsyncRepository` base class (~60 lines).

**Why:** advanced-alchemy provided far more than we needed and took control of session lifecycle in ways that conflicted with our disconnect-cancellation requirement. We need to:
- Track the PostgreSQL backend PID for `pg_cancel_backend()`
- Close connections directly for basin queries (GEOS ignores cancel)
- Guarantee cleanup on client disconnect

A thin wrapper gives full control over these behaviors.

**Trade-off:** We lose some convenience methods, but the repository surface area is small (list, get_one_or_none, plus domain-specific queries).

---

## 4. Removed Jinja2 for JSON-LD

**Decision:** Build JSON-LD responses with a pure Python builder function instead of Jinja2 templates.

**Why:** JSON-LD output is structured data, not a document. A Python function that constructs dicts is more debuggable, testable, and explicit than a template that mixes logic with output. The template was also fragile — whitespace and escaping issues were common.

---

## 5. Explicit CORS headers over framework CORSConfig

**Decision:** Set CORS headers unconditionally in middleware rather than using Litestar's `CORSConfig`.

**Why:** Litestar's CORSConfig (like most framework CORS implementations) only adds headers when it sees an `Origin` request header. Behind CloudFront or other reverse proxies that strip `Origin`, CORS headers silently disappear. Our middleware adds them unconditionally — the API is fully public, so `Access-Control-Allow-Origin: *` is always correct.

---

## 6. HEAD short-circuit middleware

**Decision:** Implement a custom middleware that returns empty 200 for HEAD requests on "heavy" endpoints (those that inject a repository or pygeoapi client).

**Why:** The Java service (Spring Boot) handles HEAD automatically by running the GET handler and stripping the body. This works but wastes a DB connection and potentially runs expensive navigation CTEs just to return headers. Our middleware detects heavy endpoints by inspecting the handler's DI signature and short-circuits before the handler executes. Lightweight endpoints (landing page, health, redirects) pass through normally.

**Trade-off:** HEAD responses don't include Content-Length (we'd need to run the query to know it). This matches the Java behavior and is acceptable for the use case.

---

## 7. Client disconnect cancellation strategy

**Decision:** Two cancellation strategies depending on query type:
- Navigation CTEs → `pg_cancel_backend()` (fast, connection reusable)
- Basin geometry (ST_Union) → close the TCP connection (GEOS ignores cancel signals)

**Why:** PostgreSQL's `pg_cancel_backend()` interrupts SQL execution within milliseconds for pure SQL operations. But PostGIS GEOS operations (ST_Union, ST_Simplify) run in a C library that doesn't check for interrupts — `pg_cancel_backend` is ignored for minutes. Closing the connection forces the OS to kill the backend immediately. This matches the Java implementation's behavior (thread interrupt closes the JDBC socket).

**Trade-off:** Closing the connection discards it from the pool, requiring a new connection on next checkout. Acceptable — a stuck connection is worse.

---

## 8. characteristic_data schema for basin queries

**Decision:** Use `characteristic_data.plusflowlinevaa_np21` and `characteristic_data.catchmentsp` for basin traversal instead of the `nhdplus` schema equivalents.

**Why:** The characteristic_data tables have better indexing for the recursive upstream walk pattern. The catchmentsp table in characteristic_data has only 3 columns vs 7 in nhdplus, reducing I/O for the ST_Union aggregation. This matches the Java implementation's approach.

---

## 9. Streaming responses for navigation results

**Decision:** Navigation and feature-navigation endpoints use `Stream` (chunked transfer) rather than buffering the full response.

**Why:** Navigation queries can return thousands of flowlines. Buffering the entire GeoJSON FeatureCollection in memory before sending wastes RAM and increases time-to-first-byte. Streaming yields bytes incrementally.

**Important detail:** The DB query completes and the connection is released *before* streaming begins. The stream iterates over an in-memory list of features. A client hangup mid-stream has no effect on the connection pool.

---

## 10. Single connection pool with cancel engine

**Decision:** One shared async engine (pool_size=10, max_overflow=30) for all requests, plus a dedicated single-connection engine for `pg_cancel_backend` calls.

**Why:** The cancel engine must be isolated from the main pool. If the main pool is exhausted (which is exactly when cancellation is most needed), a cancel call that depends on the same pool would deadlock.

**Configuration:** Statement timeout of 120s and idle-in-transaction timeout of 30s are set at the connection level via `connect_args`.

---

## 11. GeoJSONGeometry column type

**Decision:** Custom SQLAlchemy column type that wraps selects in `ST_AsGeoJSON()` automatically.

**Why:** Every geometry column in the API needs to come back as GeoJSON (not WKB). Rather than remembering to wrap every select, the column type handles it. This keeps the repository code clean — `flowline.shape` is already a GeoJSON string.

---

## 12. No deprecated endpoints

**Decision:** Three Java endpoints are intentionally not ported:
- `GET /lookups`
- `GET /lookups/{characteristicType}/characteristics`
- `GET /linked-data/{featureSource}/{featureID}/{characteristicType}`

**Why:** Project owner decision. These endpoints are deprecated and will not be supported going forward.

---

## 13. RFC 9457 Problem Details for all errors

**Decision:** Every error response uses `application/problem+json` with consistent structure (type, title, status, detail).

**Why:** The Java service returned inconsistent error formats. RFC 9457 is a standard, machine-readable format. Clients can reliably parse errors. The `instance` field on 500 errors carries a correlation ID that maps to server logs.

---

## 14. Null over empty string for missing values

**Decision:** Feature properties use `null` (not `""`) for missing values (comid, reachcode, mainstem).

**Why:** Semantically correct — a missing value is absent, not an empty string. JSON `null` is unambiguous. The Java service used empty strings in some cases, but this was inconsistent and the project owner approved the change.

---

## 15. psycopg3 (binary) over asyncpg

**Decision:** Use psycopg (v3) with the binary distribution as the async PostgreSQL driver.

**Why:** psycopg3 integrates natively with SQLAlchemy's async engine. The binary distribution bundles libpq, eliminating system library dependencies in Docker. asyncpg is faster for raw queries but doesn't integrate with SQLAlchemy ORM, which we use for the model layer.

---

## 16. uv for package management

**Decision:** Use uv for dependency resolution, virtual environments, and project management.

**Why:** Dramatically faster than pip/poetry. Single tool replaces pip, pip-tools, virtualenv, and build. Lockfile ensures reproducible installs. The team was already using it.
