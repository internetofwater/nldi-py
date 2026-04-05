# Spec: PR 4.2 — GET /linked-data/hydrolocation

## Purpose

Return the hydrologic location nearest to a provided set of coordinates. First endpoint that calls pygeoapi.

## API contract (parity with Java)

**Request:** `GET /linked-data/hydrolocation?coords=POINT(-89.509 43.087)`

**Response:** GeoJSON FeatureCollection with two features:

1. **Indexed feature** — the snapped point on the flowline network:
   - geometry: Point (the intersection point from flowtrace)
   - properties: comid, navigation URL, measure, reachcode, source="indexed"

2. **Provided feature** — the original input point:
   - geometry: Point (the coords the user provided)
   - properties: source="provided", all other fields empty

**Content-Type:** `application/geo+json`

## Flow

1. Parse WKT coords to extract lon/lat
2. POST to pygeoapi flowtrace endpoint with lon, lat, direction="none"
3. Extract intersection_point from response
4. Find catchment by spatial intersect with intersection point → get comid
5. Compute measure and reachcode from flowline for that comid
6. Build two Features, return as FeatureCollection

## WKT parsing

Pre-refactor used shapely for `from_wkt(coords).x/.y`. We can use a simple regex instead (identified in dependency decisions). Pattern: `POINT(lon lat)`.

## DB queries needed

- `CatchmentRepository.get_by_point(wkt)` — already exists
- `FlowlineRepository`: need reachcode and computed measure for a comid
  - measure = `fmeasure + (1 - ST_LineLocatePoint(shape, point)) * (tmeasure - fmeasure)`

## Error cases

- Missing coords → 400
- Invalid WKT → 400
- pygeoapi timeout → 504 (handled by client)
- No catchment found → 404
- No measure found → 404

## Dependencies

- `PyGeoAPIClient` from PR 4.1
- `CatchmentRepository.get_by_point()` from PR 2.5
- `NLDI_PYGEOAPI_URL` env var

## Acceptance criteria

- Unit tests with mocked pygeoapi responses
- Response shape matches Java (two features)
- 504 on pygeoapi timeout
- 400 on missing/invalid coords
