# Changelog

## Unreleased

### Fixed

- Errors from the upstream pygeoapi service now return ``502 Bad Gateway``
  with a problem+json response that surfaces the upstream ``description``
  (or ``detail``/``message``) in the ``detail`` field, along with an
  ``upstream_status`` field. Previously any non-timeout pygeoapi error
  (HTTP 4xx/5xx, invalid JSON, connect failure) fell through to the
  generic 500 handler and logged a full traceback.

- Browser-facing HTML landing page now generates its JSON link using the
  configured public base URL (``NLDI_URL`` + ``NLDI_PATH``) instead of
  ``request.url``. Behind a reverse proxy such as CloudFront, the link
  previously leaked the origin-facing scheme and host (e.g. the CloudFront
  distribution hostname).

- Feature responses now include `measure` property on source feature endpoints
  (`/linked-data/{source}`, `/linked-data/{source}/{id}`, and feature
  navigation), restoring parity with the Java NLDI API.

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
