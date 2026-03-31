# Spec: PR 2.3 — GET /linked-data/{source_name} (list features by source)

## Purpose

First GeoJSON endpoint. Returns a FeatureCollection of all features for a given source. Establishes the GeoJSON response pattern used by most subsequent endpoints.

## API contract (parity with Java)

**Request:** `GET /linked-data/{source_name}?f=json&limit=N&offset=N`

**Response:** GeoJSON FeatureCollection

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-120.533, 40.363]
      },
      "properties": {
        "type": "hydrolocation",
        "source": "ca_gages",
        "sourceName": "Streamgage catalog for CA SB19",
        "identifier": "ABJ",
        "name": "A&B CANAL NR JOHNSTONVILLE",
        "uri": "https://geoconnex.us/ca-gage-assessment/gages/ABJ",
        "comid": "",
        "reachcode": "18080003000359",
        "navigation": "https://.../linked-data/ca_gages/ABJ/navigation"
      }
    }
  ]
}
```

**Content-Type:** `application/geo+json` (RFC 7946 standard, replaces Java's `application/vnd.geo+json`)

**Notes:**
- `navigation` property is a computed URL: `{base_url}/linked-data/{source}/{identifier}/navigation`
- `source`, `sourceName`, `type` come from the crawler_source relationship (association proxies)
- `mainstem` property included when available
- `comid` may be empty string or integer
- Source `comid` is special — queries FlowlineModel instead of FeatureSourceModel

## Query parameters

- `f` — format (handled by existing content negotiation)
- `limit` — max features to return (default: 0 = no limit? or 1000? check Java)
- `offset` — pagination offset (default: 0)

## GeoJSON DTOs

Port from pre-refactor `struct_geojson.py` (adapted from msgspec examples):
- `Point`, `LineString`, `Polygon`, `MultiPoint`, `MultiLineString`, `MultiPolygon`
- `Feature` — geometry + properties dict + optional id
- `FeatureCollection` — list of Features

These are the message model for all GeoJSON endpoints going forward.

## Geometry serialization decision

This PR forces the `ST_AsGeoJSON` vs WKB decision:
- **Option A:** `ST_AsGeoJSON` in SQL → geometry comes back as JSON string → parse into struct
- **Option B:** WKB default → use shapely `to_shape().__geo_interface__` → dict → struct

Recommend Option A: avoids shapely dependency for this path, pushes work to DB.

## Handler logic

1. Validate source exists (query CrawlerSourceRepository)
2. If source is "comid", query FlowlineRepository; else query FeatureRepository
3. For each row, build a Feature struct with:
   - geometry from DB
   - properties mapped from model fields + association proxies
   - computed `navigation` URL
4. Return FeatureCollection

## Error cases

- Unknown source_name → 404
- Invalid `f=` → 400 (existing)

## What this PR does NOT include

- Streaming (data is materialized then returned)
- JSON-LD (Phase 5)
- comid-specific handling may be deferred to 2.4 if scope is too large

## Acceptance criteria

- Unit tests with fake repos
- Integration test against testcontainers
- Response shape matches Java (structural parity)
- `application/geo+json` content type
- Pagination works
