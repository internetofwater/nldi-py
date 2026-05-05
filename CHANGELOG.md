# Changelog

## 3.0.1

### Changed

- Basin queries use `characteristic_data` schema for better performance on basin queries


## 3.0.0

### Added

- Complete Python reimplementation of the Java NLDI service with endpoint parity
- All navigation modes: downstream main (DM), downstream with diversions (DD), upstream main (UM), upstream with tributaries (UT)
- Basin endpoint with split catchment support via pygeoapi
- Hydrolocation endpoint
- JSON-LD output format (`f=jsonld`)
- RFC 9457 problem+json error responses with reference IDs
- Content negotiation via `f=` query parameter with browser redirect
- Explicit CORS, Cache-Control, and Vary headers via middleware
- Legacy redirects (`/swagger-ui/index.html` → `/docs`, `/openapi` → `/docs`)
- Health check with DB and pygeoapi status reporting, pool stats
- Disconnect guard: cancels in-flight DB queries on client disconnect
- Streaming GeoJSON serialization for navigation responses
- Parity tests against Java NLDI golden files
- Integration tests via testcontainers with PostGIS
- Load testing with Locust

### Changed

- Framework: Lighter database stack using SQLAlchemy async (replaced advanced-alchemy)
- DB driver: psycopg3 (replaced asyncpg)
- Geometry serialization: `ST_AsGeoJSON` custom column type (eliminated runtime shapely dependency)
- Navigation queries use joined loads (eliminated N+1 queries)
- Controllers split into sub-modules (lookups, navigation, basin)

### Removed

- advanced-alchemy dependency (replaced with ~15-line `AsyncRepository` base)
- Jinja2 dependency (JSON-LD built with Python builder)
- Deprecated endpoints: `/lookups`, characteristic data endpoints
