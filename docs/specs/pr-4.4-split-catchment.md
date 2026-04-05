# Spec: PR 4.4 — Basin split catchment

## Purpose

When `splitCatchment=true` and the feature is a point, split the local catchment at the feature's position on the flowline. This produces a more precise upstream basin boundary.

## Preconditions

- `splitCatchment=true` query parameter
- Feature is a point geometry (not a line/polygon)
- Source is not "comid" (comid features are flowlines, not points)

If preconditions aren't met, fall through to the simple basin path (already implemented in 4.3).

## Logic: find a point on the flowline

Three fallback strategies to locate the feature's position on the flowline:

### Plan A: Interpolate from measure
If the feature has a `measure` value, use `ST_LineInterpolatePoint` to find the point along the flowline at that measure. This is the most accurate method.

Query: join feature → flowline by comid, compute `ST_LineInterpolatePoint(shape, scaled_measure)`, return (lon, lat).

### Plan B: Nearest point on flowline
If Plan A fails (no measure), compute `ST_Distance` between the feature location and its flowline. If within threshold (200m), use `ST_ClosestPoint` to snap to the flowline.

Queries:
- `ST_Distance(feature.location, flowline.shape, false)` → distance in meters
- `ST_ClosestPoint(flowline.shape, feature.location)` → (lon, lat)

### Plan C: pygeoapi flowtrace
If Plans A and B fail, use the feature's raw coordinates to call pygeoapi flowtrace (same as hydrolocation). Extract the intersection point.

## Logic: split the catchment

Once we have a point on the flowline, POST to pygeoapi splitcatchment endpoint:
- URL: `{pygeoapi_url}/processes/nldi-splitcatchment/execution`
- Payload: lon, lat, upstream=true
- Timeout: 2x normal (split is slow)
- Response contains a feature with id "mergedCatchment" or "drainageBasin"

Return that feature as the basin geometry.

## New components

### FlowlineRepository methods (port from pre-refactor)
- `feat_get_point_along_flowline(feature_id, source)` → (lon, lat) or None
- `feat_get_distance_from_flowline(feature_id, source)` → float or None
- `feat_get_nearest_point_on_flowline(feature_id, source)` → (lon, lat) or None

### PyGeoAPIClient method
- `splitcatchment(lon, lat)` → dict (the merged catchment feature)

### Handler changes
- Basin handler: add split catchment path when `splitCatchment=true` and feature is a point
- Resolve feature geometry type to decide which path

## WKT parsing
Use `parse_wkt_point()` from util.py — no shapely needed for the splitcatchment payload.

## Error cases
- splitCatchment with comid source → 400 (already handled)
- All three plans fail to find a point → 404 "Unable to retrieve point on flowline"
- pygeoapi splitcatchment timeout → 504
- pygeoapi returns no mergedCatchment/drainageBasin feature → 500

## Acceptance criteria
- Unit tests with mocked pygeoapi and fake repos
- Plan A/B/C fallback logic tested
- Split catchment response has polygon geometry
- Timeout → 504
