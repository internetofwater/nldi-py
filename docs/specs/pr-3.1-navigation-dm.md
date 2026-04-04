# Spec: PR 3.1 — Navigation infrastructure + DM mode

## Purpose

Establish the navigation query pattern with the simplest mode (Downstream Main). This PR introduces the CTE infrastructure, the "resolve starting comid" logic, and the flowline navigation endpoint.

## API contract (parity with Java)

**Request:** `GET /linked-data/{source}/{id}/navigation/DM/flowlines?distance=10`

**Response:** GeoJSON FeatureCollection of flowlines along the navigation path.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "LineString", "coordinates": [...]},
      "properties": {"nhdplus_comid": "13293396"},
      "id": 13293396
    }
  ]
}
```

**Notes:**
- Java returns minimal properties on nav flowlines — just `nhdplus_comid` as a string
- We return `nhdplus_comid` as int (per project owner preference on comid typing)
- `distance` parameter in km, required
- Content-Type: `application/geo+json`

## New components

### Navigation query builder (`src/nldi/db/navigation.py`)
- `NavigationModes` enum (DM, DD, UM, UT)
- `NAV_DIST_DEFAULTS` — default distances per mode
- `dm(comid, distance, coastal_fcode)` → returns a `Select` of comids
- Uses `bindparam()` instead of `text(":param")` for cleaner parameter binding
- Recursive CTE: anchor on starting comid, walk downstream following `dnhydroseq` on same `terminalpathid`

### Resolve starting comid
- Shared logic: if source is "comid", use directly; else look up feature → get comid
- Validates source/identifier exist, raises 404/400 appropriately

### Flowline navigation handler
- Replace `get_flowline_navigation` stub
- Validate start, build nav query, join to FlowlineModel, return FeatureCollection
- `distance` parameter with default from `NAV_DIST_DEFAULTS`

## Query flow

```
source/identifier → resolve comid → DM CTE → list of comids → join FlowlineModel → FeatureCollection
```

## Error cases

- Unknown source → 404
- Unknown identifier → 404
- Invalid comid → 400
- Invalid nav_mode → 400 (only DM in this PR; others return 501)

## What this PR does NOT include

- DD, UM, UT modes (PR 3.2)
- Feature navigation by data source (PR 3.3)
- Trim start / trim tolerance
- excludeGeometry parameter

## Acceptance criteria

- Unit tests with fake repos (nav query returns comid list)
- Integration test: DM navigation from known comid returns flowlines
- `task check` + `task typecheck` pass
