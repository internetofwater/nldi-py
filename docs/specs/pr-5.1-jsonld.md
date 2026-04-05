# Spec: PR 5.1 — JSON-LD support (f=jsonld)

## Purpose

When `f=jsonld` is requested, return a JSON-LD graph instead of GeoJSON. Uses `application/ld+json` content type. Applies to feature endpoints only.

## Which endpoints support JSON-LD

- `GET /linked-data/{source_name}` — list features by source
- `GET /linked-data/{source_name}/{identifier}` — single feature
- `GET /linked-data/{source_name}/{identifier}/navigation/{nav_mode}/{data_source}` — navigated features

NOT supported on:
- List sources (returns JSON array, not features)
- Navigation flowlines (minimal properties, no linked data semantics)
- Basin (polygon, no feature properties)
- Hydrolocation (special two-feature response)
- Navigation modes/info (JSON, not features)

## Response shape

Content-Type: `application/ld+json`

### Single feature (`f=jsonld`):
```json
{
  "@context": [{ ... vocabularies ... }],
  "@id": "<feature uri>",
  "@type": "hyf:HY_HydroLocation",
  "schema:subjectOf": {
    "@type": "schema:CreativeWork",
    "schema:identifier": "<source>",
    "schema:name": "<sourceName>"
  },
  "name": "<feature name>",
  "comid": "https://geoconnex.us/nhdplusv2/comid/<comid>",
  "hyf:referencedPosition": [ ... optional mainstem, measure, reachcode ... ],
  "geo": { "@type": "schema:GeoCoordinates", "schema:longitude": <lon>, "schema:latitude": <lat> },
  "gsp:hasGeometry": { ... WKT point ... }
}
```

### Collection (`f=jsonld`):
```json
{
  "@context": [{ ... }],
  "@id": "_:graph",
  "@graph": [ ... array of feature objects as above ... ]
}
```

## @context vocabulary

Fixed — same every time:
```json
{
  "schema": "https://schema.org/",
  "geo": "schema:geo",
  "hyf": "https://www.opengis.net/def/schema/hy_features/hyf/",
  "gsp": "http://www.opengis.net/ont/geosparql#",
  "name": "schema:name",
  "comid": { "@id": "schema:geoWithin", "@type": "@id" },
  "hyf:linearElement": { "@type": "@id" }
}
```

## Implementation

### `src/nldi/jsonld.py`

Pure Python builder — no template engine.

- `JSONLD_CONTEXT` — the fixed context dict
- `feature_to_jsonld(props: dict, geometry: dict | None) -> dict` — convert one feature
- `to_jsonld_graph(features: list[dict]) -> dict` — wrap multiple features in @graph
- `to_jsonld_single(feature: dict) -> dict` — single feature (no @graph wrapper)

### Handler changes

In the three supported endpoints, check `f == "jsonld"`:
- Build features as usual (same DB queries)
- Instead of wrapping in FeatureCollection, pass to jsonld builder
- Return with `media_type=MediaType.JSONLD`

### Content negotiation

Already handled — `f=jsonld` passes validation. Just need to branch on it in the handlers.

## Conditional fields

- `comid` — only included if present, formatted as geoconnex URI
- `mainstem` — only if not None/NA, as hyf:linearElement
- `measure` + `reachcode` — only if both present, as hyf:distanceExpression
- `geo` + `gsp:hasGeometry` — only for Point geometry

## Acceptance criteria

- Unit tests: builder produces correct structure for feature with all fields
- Unit tests: builder handles missing optional fields
- Unit tests: single vs collection output
- Endpoint test: `f=jsonld` returns `application/ld+json`
- Parity: output matches Java response structure
