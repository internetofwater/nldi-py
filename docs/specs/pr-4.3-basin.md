# Spec: PR 4.3 — GET /linked-data/{source}/{id}/basin

## Purpose

Compute the upstream drainage basin polygon for a feature. Two paths: simple (aggregate catchments by comid) and split catchment (requires pygeoapi).

## API contract (parity with Java)

**Request:** `GET /linked-data/{source}/{id}/basin?simplified=true&splitCatchment=false`

**Response:** GeoJSON FeatureCollection with one Feature — a Polygon/MultiPolygon of the aggregated upstream basin.

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [...]},
    "properties": {}
  }]
}
```

**Content-Type:** `application/geo+json`

**Parameters:**
- `simplified` (bool, default true) — simplify geometry with ST_Simplify
- `splitCatchment` (bool, default false) — split the local catchment at the feature point

## Two paths

### Simple path (splitCatchment=false or source=comid)
1. Resolve comid from source/identifier
2. Recursive CTE: walk upstream collecting all comids (similar to UT but unbounded)
3. ST_Union all catchment polygons for those comids
4. Optionally ST_Simplify
5. Return as single Feature with empty properties

### Split catchment path (splitCatchment=true, point feature)
Complex — requires finding a point on the flowline, then calling pygeoapi splitcatchment service. Three fallback strategies from pre-refactor:
- Plan A: interpolate point along flowline using measure
- Plan B: find nearest point on flowline (if within threshold)
- Plan C: use pygeoapi flowtrace to find intersection point

Then POST to pygeoapi splitcatchment endpoint.

## Implementation approach

Start with the simple path only. Split catchment is a follow-up — it's the most complex single feature in the API and deserves its own PR if needed.

## DB query: drainage basin CTE

Recursive CTE walking upstream (all tributaries, no distance limit):
- Anchor: starting comid
- Recursive: follow dnhydroseq and dnminorhyd upstream
- Join to catchmentsp, ST_Union geometries, optionally ST_Simplify
- Return ST_AsGeoJSON of the result

## Error cases

- Unknown source → 404
- Unknown identifier → 404
- No basin found → 404
- splitCatchment with comid source → 400

## Acceptance criteria

- Simple basin returns polygon geometry
- simplified=true produces simpler geometry
- Empty properties (matches Java)
- Unit tests with fakes
- Integration test against testcontainers
