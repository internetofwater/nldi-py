# Spec: Streaming navigation responses

## Problem

Navigation endpoints (`/flowlines`, `/{data_source}`) build a complete
`FeatureCollection` in memory before writing any bytes to the client.
For large result sets this means the client waits for full JSON
serialization before receiving the first byte. Time-to-first-byte is
poor even when the DB query itself is fast.

## Solution

Stream the GeoJSON `FeatureCollection` response by yielding the opening
wrapper, then each serialized `Feature`, then the closing wrapper — as
the in-memory result list is iterated. The DB query is unchanged; the
full result list is materialized before streaming begins.

---

## Design

### What changes

A shared generator in `geojson.py`:

```python
def stream_feature_collection(features: list[Feature]) -> Iterator[bytes]:
    yield b'{"type":"FeatureCollection","features":['
    for i, feat in enumerate(features):
        if i > 0:
            yield b","
        yield msgspec.json.encode(feat)
    yield b"]}"
```

Both nav endpoints return a Litestar `Stream` instead of a `Response`:

```python
from litestar.response import Stream

return Stream(stream_feature_collection(features), media_type=MediaType.GEOJSON)
```

### Connection pool safety

By the time streaming starts, the DB query has returned and the session is
closed. The pool connection is back in the pool before the first byte is
sent. A client hangup mid-stream is a network event only — no DB state is
involved. The disconnect guard's `_cancel_pid` is `None` by this point, so
any watcher firing during streaming is a no-op.

Streaming *improves* the pool story slightly: the connection is returned
right after the query rather than being held while the full response is
serialized.

### What does not change

- The DB query — `from_nav_query`, `from_trimmed_nav_query` still return
  a fully materialized list. The DB connection is returned to the pool
  before the first byte is streamed.
- `excludeGeometry` — applied to the list before passing to the generator,
  no change needed.
- The disconnect guard — `_cancel_pid` is cleared after the query returns.
  A client disconnect during streaming is a no-op cancel, handled cleanly.
- The `jsonld` format path in `get_feature_navigation` — JSON-LD requires
  a complete graph object; it is not streamed and remains a standard
  `Response`.
- Error handling before streaming starts — 4xx errors raised during
  COMID resolution or parameter validation are returned normally before
  any streaming begins.

### Error handling caveat

Once streaming starts the HTTP status `200` is already sent. An exception
mid-stream (e.g. serialization error on a malformed geometry) will result
in a truncated response rather than a clean error status. This is
acceptable: the data is already in memory and serialization errors on
`msgspec` structs are not expected in practice.

---

## Scope

Only the two GeoJSON navigation endpoints:

- `GET /{source}/{id}/navigation/{mode}/flowlines` (`get_flowline_navigation`)
- `GET /{source}/{id}/navigation/{mode}/{data_source}` (`get_feature_navigation`)

Basin and all non-navigation endpoints are out of scope.

---

## Testing

- Unit: assert streamed bytes concatenate to valid GeoJSON with correct
  feature count.
- Unit: assert empty result streams to `{"type":"FeatureCollection","features":[]}`.
- Existing integration tests cover the full endpoint response; verify they
  still pass by joining streamed chunks and parsing JSON.

---

## Plan

| Step | Description |
|------|-------------|
| 1 | Add `stream_feature_collection` generator to `geojson.py` |
| 2 | Update `get_flowline_navigation` to return `Stream` |
| 3 | Update `get_feature_navigation` GeoJSON path to return `Stream` |
| 4 | Unit tests for the generator |
