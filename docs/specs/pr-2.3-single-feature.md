# Spec: PR 2.3 — GET /linked-data/{source_name}/{identifier} (single feature)

Reordered from original roadmap — single feature before list features, since it establishes the GeoJSON pattern on the simplest case.

## Purpose

First GeoJSON endpoint. Returns a single feature by source and identifier. Establishes GeoJSON DTOs, geometry serialization, and the Feature-building pattern used by all subsequent GeoJSON endpoints.

## API contract (parity with Java)

**Request:** `GET /linked-data/{source_name}/{identifier}`

**Response:** GeoJSON FeatureCollection containing one Feature.

Note: Java returns a FeatureCollection even for a single feature. We match this.

### Feature source example (wqp):
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-89.509, 43.087]},
    "properties": {
      "identifier": "USGS-054279485",
      "navigation": "https://.../linked-data/wqp/USGS-054279485/navigation",
      "name": "STRICKER'S POND AT MIDDLETON, WI",
      "source": "WQP",
      "sourceName": "Water Quality Portal",
      "comid": "13294314",
      "type": "varies",
      "uri": "https://www.waterqualitydata.us/provider/NWIS/USGS-WI/USGS-054279485/",
      "mainstem": "https://geoconnex.us/ref/mainstems/575519"
    }
  }]
}
```

### Comid example:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {"type": "LineString", "coordinates": [...]},
    "properties": {
      "identifier": "13294314",
      "navigation": "https://.../linked-data/comid/13294314/navigation",
      "source": "comid",
      "sourceName": "NHDPlus comid",
      "comid": "13294314"
    }
  }]
}
```

**Content-Type:** `application/geo+json`

## New components introduced

### GeoJSON DTOs (`src/nldi/geojson.py`)
Port from pre-refactor `struct_geojson.py` (msgspec structs):
- Geometry types: Point, LineString, Polygon, Multi* variants
- Feature: geometry + properties dict + optional id
- FeatureCollection: list of Features

### Geometry serialization
Use `ST_AsGeoJSON` in SQL queries. Geometry comes back as a JSON string from the DB, parsed into the appropriate geometry struct. Avoids shapely for this path.

## Handler logic

1. If source is "comid":
   - Parse identifier as int (400 if not valid)
   - Query FlowlineRepository.get(comid)
   - Build Feature with LineString geometry, comid-specific properties
2. Else:
   - Validate source exists via CrawlerSourceRepository → 404 if not
   - Query FeatureRepository by source + identifier → 404 if not found
   - Build Feature with Point geometry, full properties including association proxies
3. Compute `navigation` URL: `{base_url}/linked-data/{source}/{identifier}/navigation`
4. Wrap in FeatureCollection, return with `media_type=MediaType.GEOJSON`

## Error cases

- Unknown source → 404
- Unknown identifier → 404
- Invalid comid (not an integer) → 400

## Acceptance criteria

- GeoJSON structs serialize correctly (unit test)
- Feature properties match Java shape (unit test with fakes)
- 404 for missing source/identifier (unit test)
- Integration test: query real feature from testcontainers
- Content-Type is `application/geo+json`
