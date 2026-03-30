# NLDI-py Dependency Decisions

## Keep

| Dependency | Role | Justification |
|---|---|---|
| Litestar | ASGI framework | DI, DTO layer, OpenAPI generation. See framework-decision.md |
| SQLAlchemy (async) | Database access | Query builder, async sessions, ORM for table mapping. The ecosystem standard. |
| GeoAlchemy2 | PostGIS support | Spatial column types and functions (ST_Intersects, ST_Union, etc.). No real alternative. |
| asyncpg | Async PostgreSQL driver | Required by SQLAlchemy async. Fast, well-maintained. |
| httpx | Async HTTP client | For pygeoapi calls. Async-native, timeout support. |

## Drop

| Dependency | Role | Reason to drop |
|---|---|---|
| advanced-alchemy | ORM repository/service layer + Litestar plugin | Most queries bypass it. Repository pattern adds indirection without value for read-only geospatial queries. Session wiring can be done with plain SQLAlchemy + Litestar DI. |
| Jinja2 | Response templating | Only justified for JSON-LD. GeoJSON FeatureCollection rendering is just `json.dumps` with a wrapper. Evaluate whether JSON-LD can be built without it. |

## Evaluate

| Dependency | Role | Question |
|---|---|---|
| shapely | Geometry manipulation | Direct usage is trivial: WKT point parsing (replaceable with regex) and `to_shape().__geo_interface__` in geo.py (replaceable with `ST_AsGeoJSON` in SQL). However, GeoAlchemy2 depends on shapely transitively for `to_shape()`. Fully dropping it means avoiding `to_shape()` entirely — use database-side GeoJSON conversion instead. Existing issue #46 tracks this. |
| msgspec | Struct definitions + serialization | Originally chosen as a lighter alternative to dataclasses with fast serialization and good Litestar integration. Evaluate whether Litestar DTOs + standard serialization cover the same ground. |
