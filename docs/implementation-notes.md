# NLDI-py Implementation Notes

Capture decisions and details that aren't principles but will matter when writing code.

## Deprecated endpoints (not porting)

The following Java endpoints are deprecated by project owner decision and will not be
implemented in the Python version:

- `GET /lookups` — list characteristic types
- `GET /lookups/{characteristicType}/characteristics` — list characteristics by type
- `GET /linked-data/{featureSource}/{featureID}/{characteristicType}` — characteristic data for a feature

## Bugs inherited from Java

- Landing page link relations: both HTML and JSON OpenAPI links use `rel: "service-desc"`. The
  HTML link should be `rel: "service-doc"` per OGC API conventions. Java has the same bug.

## Geometry serialization: ST_AsGeoJSON vs WKB

GeoAlchemy2 returns WKB by default, which requires shapely to convert to GeoJSON. An alternative is
using `ST_AsGeoJSON` in SQL (either per-query or via a custom column type), which returns GeoJSON text
directly and eliminates the need for shapely deserialization. Tradeoff: GeoJSON is 2-3x larger than
WKB on the wire between DB and app, but skips the Python-side conversion step. Benchmark before deciding.

## Fast-return HEAD

HEAD support should be implemented as middleware that returns 200 + appropriate headers without
executing the route handler. This avoids running expensive DB queries just to discard the body (which
is what Spring Boot does on the Java side).

## Content negotiation / browser redirect

The `f=` query parameter is not standard content negotiation. When `f=` is absent and `Accept` includes
`text/html`, the app assumes a browser and returns a canned HTML page with a link to `?f=json`. This is
a pre-request concern that applies to all linked-data endpoints.

## Database error handling

DB connection errors and timeouts currently fall through to the catch-all 500 handler. A dedicated exception handler for `sqlalchemy.exc.OperationalError` should be added to return 503 Service Unavailable with a problem+json response. Register alongside the existing handlers in `create_app`. Cross-cutting — covers all DB-backed endpoints in one place.

## Null vs empty string for missing values

Feature properties use `null` (not empty string) for missing values (comid, reachcode, mainstem). This differs from the Java implementation which uses empty strings in some cases. Follow up with project owner to confirm this is acceptable.

## Phase 3: Navigation CTE readability

The four navigation CTEs (DM, DD, UM, UT) share ~70% of their structure. Port as-is first (working system), then refactor for readability:

- Replace `text(":param")` with `sqlalchemy.bindparam()` — type-safe, cleaner
- Consider a builder function for the common CTE structure (anchor + recursive step + distance filter)
- Extract "resolve starting comid" logic shared by `walk_flowlines` and `walk_features`
- Keep the inline SQL comments showing expected compiled output — they're valuable for debugging
