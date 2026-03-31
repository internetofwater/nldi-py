# Spec: PR 2.4 — GET /linked-data/{source_name} (list features by source)

Reordered from original roadmap — list features after single feature, since 2.3 establishes the GeoJSON pattern.

## Purpose

Returns all features for a given source as a GeoJSON FeatureCollection. Builds on the Feature-building pattern from PR 2.3. Adds pagination.

## API contract (parity with Java + pagination improvement)

**Request:** `GET /linked-data/{source_name}?limit=N&offset=N`

**Response:** GeoJSON FeatureCollection.

Same Feature shape as 2.3, but many features. Java returns all features with no pagination controls. We add optional `limit` and `offset` as an improvement.

**Content-Type:** `application/geo+json`

### Pagination

- `limit` — max features to return. Default: 0 (no limit, matches Java behavior)
- `offset` — skip N features. Default: 0

Java does not support pagination — this is an additive improvement. Clients that don't send pagination params get the same result as Java.

## Handler logic

1. Validate source exists → 404 if not
2. If source is "comid", query FlowlineRepository with pagination; else query FeatureRepository
3. For each row, build Feature (same pattern as 2.3)
4. Return FeatureCollection

## Dependencies on 2.3

- GeoJSON DTOs (already created)
- Geometry serialization pattern (already established)
- Feature-building logic (reuse/extract from 2.3 handler)
- Fake repos (extend with list methods)

## Error cases

- Unknown source → 404

## Acceptance criteria

- Unit tests with fake repos (empty source, source with features, pagination)
- Integration test against testcontainers
- Default behavior (no limit/offset) returns all features
- Pagination limits and offsets work
- Content-Type is `application/geo+json`
