# NLDI-py Dependencies

## In use

| Dependency | Role | Justification |
| --- | --- | --- |
| Litestar | ASGI framework | DI, DTO layer, OpenAPI generation |
| SQLAlchemy (async) | Database access | Query builder, async sessions, ORM for table mapping |
| GeoAlchemy2 | PostGIS support | Spatial column types and functions (ST_Intersects, ST_Union, etc.) |
| asyncpg | Async PostgreSQL driver | Required by SQLAlchemy async |
| httpx | Async HTTP client | For pygeoapi calls. Async-native, timeout support |
| msgspec | Struct definitions + serialization | GeoJSON DTOs, DataSource. Works well with Litestar serialization |

## Removed during refactor

| Dependency | Reason |
| --- | --- |
| advanced-alchemy | Replaced with minimal `AsyncRepository` base class (~15 lines) and explicit session lifecycle. Gives full control over connection cleanup on client disconnect. |
| Jinja2 | JSON-LD built with a Python builder, no templating needed. GeoJSON rendering is just `json.dumps` with a wrapper. |
