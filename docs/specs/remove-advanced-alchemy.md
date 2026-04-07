# Plan: Remove advanced-alchemy dependency

## Problem

Advanced-alchemy wraps SQLAlchemy exceptions in `RepositoryError`, owns the
session lifecycle, and installs its own exception handler. This prevents us
from cleanly handling client disconnects, pool timeouts, and query
cancellation — causing zombie DB connections under load.

## What advanced-alchemy provides today

1. **`SQLAlchemyPlugin`** — creates the async engine, manages the connection
   pool, provides `db_session` via Litestar DI
2. **`SQLAlchemyAsyncRepository`** — base class for our 4 repos, provides
   `list()`, `get_one_or_none()`, and `self.session`
3. **`EngineConfig`** — thin wrapper around `create_async_engine()` kwargs
4. **Exception wrapping** — `wrap_sqlalchemy_exception` converts all
   SQLAlchemy errors to `RepositoryError`
5. **`before_send_handler`** — optional session commit/rollback on response

## What we actually use from the repository base

- `self.list(statement=stmt)` — executes a SELECT, returns model instances
- `self.get_one_or_none(...)` — executes a filtered SELECT, returns one or None
- `self.session.execute(stmt)` — raw session execute (6 call sites)

That's it. No create/update/delete, no bulk operations, no upsert.

## Replacement plan

### Step 1: Engine + session provider (`src/nldi/db/__init__.py`)

Replace `SQLAlchemyPlugin` with direct engine creation and a Litestar
dependency that provides a session per request with guaranteed cleanup:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=10,
            pool_timeout=60,
            connect_args={"server_settings": {"statement_timeout": "120000"}},
        )
    return _engine

async def provide_db_session():
    engine = get_engine()
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

Key difference: we own the `try/except/finally`. On client disconnect
(`CancelledError`), the finally block closes the session and returns the
connection to the pool.

### Step 2: Replace repository base class (`src/nldi/db/repos.py`)

Replace `SQLAlchemyAsyncRepository` with a minimal base:

```python
class AsyncRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, statement):
        result = await self.session.execute(statement)
        return list(result.scalars())

    async def get_one_or_none(self, statement):
        result = await self.session.execute(statement)
        return result.scalars().one_or_none()
```

Each repo changes its base class and adjusts `list()` / `get_one_or_none()`
calls to pass a full statement instead of filter kwargs.

### Step 3: Update DI providers (`src/nldi/controllers/linked_data/__init__.py`)

Current providers use advanced-alchemy's auto-injected `db_session`.
Replace with explicit injection from our `provide_db_session`:

```python
async def provide_source_repo(db_session: AsyncSession) -> CrawlerSourceRepository:
    return CrawlerSourceRepository(session=db_session)
```

### Step 4: Update `asgi.py`

- Remove `SQLAlchemyPlugin`, `SQLAlchemyAsyncConfig`, `EngineConfig` imports
- Remove `_db_plugin()` function
- Add `db_session` to the `dependencies` dict
- Remove `RepositoryError` from exception handlers (no longer raised)
- Keep `sqlalchemy.exc.OperationalError` and `sqlalchemy.exc.TimeoutError`
  handlers (these will now propagate directly)

### Step 5: Update exception handlers

Without advanced-alchemy wrapping, SQLAlchemy exceptions reach our handlers
directly. Simplify to:

```python
exception_handlers={
    HTTPException: problem_details_handler,
    PyGeoAPITimeoutError: gateway_timeout_handler,
    sqlalchemy.exc.OperationalError: db_unavailable_handler,
    sqlalchemy.exc.TimeoutError: db_unavailable_handler,
    TimeoutError: db_unavailable_handler,
    Exception: unhandled_exception_handler,
}
```

### Step 6: Update unit test fakes

The fake repos in `tests/unit/conftest.py` don't inherit from
advanced-alchemy — they're already plain classes. No changes needed.

### Step 7: Update integration tests

Integration test conftest creates its own engine/session. May need minor
adjustments to match the new session provider pattern.

### Step 8: Remove dependency

- Remove `advanced-alchemy` from `pyproject.toml` dependencies
- Run `uv sync` to clean the lockfile

## Files changed

| File | Change |
|---|---|
| `src/nldi/db/__init__.py` | Add engine singleton + session provider |
| `src/nldi/db/repos.py` | Replace base class, adjust list/get_one_or_none |
| `src/nldi/asgi.py` | Remove plugin, wire session DI, simplify exception handlers |
| `src/nldi/controllers/linked_data/__init__.py` | Update DI providers |
| `src/nldi/errors.py` | No change (handlers already correct) |
| `tests/unit/conftest.py` | No change (fakes are plain classes) |
| `tests/integration/conftest.py` | Minor session setup adjustment |
| `pyproject.toml` | Remove advanced-alchemy |

## What we gain

- **Full session lifecycle control** — guaranteed rollback+close on error,
  cancellation, and client disconnect
- **No exception wrapping** — SQLAlchemy errors propagate directly to our
  handlers
- **No hidden exception handler** — no `set_default_exception_handler` needed
- **Simpler dependency tree** — one less package
- **Debuggable** — no middleware between our code and SQLAlchemy

## What we lose

- Repository pattern convenience methods (but we only use 2, trivially replaced)
- Auto-DI of `db_session` (replaced with explicit provider)
- `EngineConfig` wrapper (replaced with direct kwargs)

## Risk

Low. The repos are thin wrappers already. Most methods use
`self.session.execute()` directly. The fake repos in unit tests don't
touch advanced-alchemy at all. The main risk is getting the session
lifecycle right in the provider — but that's exactly what we're trying
to fix.

## Estimated effort

~2 hours. Most changes are mechanical (swap base class, adjust imports).
The session provider is the only new code (~15 lines).
