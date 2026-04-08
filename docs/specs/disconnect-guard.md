# Spec: Disconnect guard + pool health reporting

## Problem

When clients disconnect mid-request, in-flight navigation queries continue
running on RDS for up to 120s (statement_timeout). Pool connections stay
checked out, causing exhaustion and cascading 503s on subsequent requests.

## Solution

Two changes:

1. **Disconnect guard** — repos that run expensive queries record the
   Postgres backend PID and cancel it via `pg_cancel_backend` when the
   client disconnects.
2. **Pool health** — expose connection pool stats in the health endpoint
   for monitoring and testing.

---

## Part 1: Disconnect guard

### Scope

Only the three repo methods that run navigation CTEs:

- `FlowlineRepository.from_nav_query()`
- `FlowlineRepository.from_trimmed_nav_query()`
- `CatchmentRepository.get_drainage_basin()`

All other queries (feature lookups, source list, single comid) complete
in seconds and don't need cancellation.

### Design

#### PID tracking in the repo

Before executing the expensive query, the repo records the Postgres
backend PID in a request-scoped location. After the query completes
(success or error), it clears the PID.

```python
async def from_nav_query(self, nav_query):
    pid = await self.session.scalar(text("SELECT pg_backend_pid()"))
    self._cancel_pid = pid
    try:
        subq = nav_query.subquery()
        stmt = select(FlowlineModel).join(subq, ...)
        return list(await self.list(statement=stmt))
    finally:
        self._cancel_pid = None
```

#### Cancel method on the repo

```python
async def cancel_running_query(self):
    pid = getattr(self, "_cancel_pid", None)
    if pid:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT pg_cancel_backend(:pid)"),
                {"pid": pid},
            )
            await conn.commit()
```

Uses a separate connection from the pool — not the stuck one.

#### Middleware triggers cancellation

The disconnect guard middleware monitors `receive` for disconnect events.
Applied only to the linked-data Router (navigation queries live there).

```python
async def disconnect_guard_middleware(app):
    async def middleware(scope, receive, send):
        if scope["type"] != "http":
            await app(scope, receive, send)
            return

        disconnect = asyncio.Event()

        original_receive = receive
        async def guarded_receive():
            msg = await original_receive()
            if msg["type"] == "http.disconnect":
                disconnect.set()
            return msg

        handler = asyncio.create_task(
            app(scope, guarded_receive, send)
        )

        async def watch():
            await disconnect.wait()
            # Cancel any tracked query
            for dep in scope.get("_repos", []):
                await dep.cancel_running_query()
            handler.cancel()

        watcher = asyncio.create_task(watch())

        try:
            await handler
        except asyncio.CancelledError:
            pass
        finally:
            watcher.cancel()

    return middleware
```

#### Repos register themselves in scope

The DI providers store repo references in scope so the middleware can
find them:

```python
async def provide_flowline_repo(db_session, scope):
    repo = FlowlineRepository(session=db_session)
    scope.setdefault("_repos", []).append(repo)
    return repo
```

### What this does NOT change

- Session lifecycle — still one session per request via `provide_db_session`
- Fast queries — no PID tracking, no overhead
- Error handling — `QueryCanceledError` already caught by `SQLAlchemyError`
  umbrella → 503

---

## Part 2: Pool health reporting

### Change

Add pool stats to the health endpoint response under `db.pool`:

```json
{
  "db": {
    "name": "db",
    "cfg": "dev-nwis.usgs.gov",
    "status": "online",
    "pool": {
      "size": 10,
      "checked_in": 8,
      "checked_out": 2,
      "overflow": 0
    }
  }
}
```

### Implementation

In `health.py`, after the DB connectivity check:

```python
from nldi.db import get_engine

engine = get_engine()
pool = engine.pool
return {
    ...,
    "pool": {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }
}
```

---

## Testing

### Unit tests

- Repo records `_cancel_pid` before execute, clears after
- `cancel_running_query()` with no PID is a no-op
- `cancel_running_query()` with a PID calls `pg_cancel_backend`

### Integration tests

- Start a navigation query via TestClient against containerized DB
- Verify PID is set during query execution
- Verify pool stats reflect checked-out connection
- After query completes, verify PID cleared and connection returned

### Load test (acceptance)

- Back-to-back `task test:load` without restarting the app
- Monitor `checked_out` via health endpoint between runs
- Success: second run failure rate comparable to first run
- Success: `checked_out` returns to baseline within seconds of
  Locust stopping (not 120s)

### Health endpoint test

- Integration test: verify `pool` key present in health response
- System test: verify pool stats are reasonable numbers

---

## Plan

| Step | Description |
|------|-------------|
| 1 | Add pool stats to health endpoint |
| 2 | Add `_cancel_pid` tracking + `cancel_running_query()` to repos |
| 3 | Disconnect guard middleware on linked-data Router |
| 4 | DI providers register repos in scope |
| 5 | Unit tests for PID lifecycle and cancel |
| 6 | Integration + load test verification |

## Risks

- Extra `SELECT pg_backend_pid()` per navigation query (~1ms)
- `pg_cancel_backend` uses a pool connection — under extreme exhaustion
  this connection may also be unavailable. Mitigation: the cancel query
  is tiny and fast; it will get a connection before the 60s pool_timeout.
- If query finishes between disconnect and cancel, the cancel is a no-op
