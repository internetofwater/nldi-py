# Spec: Parity tests against Java NLDI service

## Purpose

Verify that our Python NLDI produces structurally equivalent responses to the
production Java service at `https://api.water.usgs.gov/nldi`. Not byte-for-byte
equality — structural and semantic parity.

## Golden file strategy

Two tiers based on response size:

### Tier 1: Full golden files (geometry stripped)

For single-feature and small responses. Store the complete JSON response with
all `geometry` fields set to `null`. Endpoints:

- `GET /linked-data?f=json` — source list (small array)
- `GET /linked-data/wqp/USGS-05427930?f=json` — single feature
- `GET /linked-data/comid/13293396?f=json` — comid feature
- `GET /linked-data/comid/13293396/navigation?f=json` — navigation modes
- `GET /linked-data/wqp/USGS-05427930?f=jsonld` — single feature JSON-LD

### Tier 2: Summary golden files

For collection/navigation endpoints that return many features. Store a summary:

```json
{
  "endpoint": "<path with query params>",
  "captured": "<ISO timestamp>",
  "feature_count": 47,
  "content_type": "application/geo+json",
  "property_keys": ["source", "sourceName", "identifier", "name", "uri", "comid", "navigation"],
  "geometry_types": ["Point"],
  "sources_present": ["WQP"],
  "first_feature": { "properties": { ... }, "geometry": null }
}
```

Endpoints:

- `GET /linked-data/wqp?f=json` — features by source (large)
- `GET /linked-data/comid/13293396/navigation/DM/flowlines?distance=10&f=json`
- `GET /linked-data/comid/13293396/navigation/DM/wqp?distance=50&f=json`
- `GET /linked-data/comid/13293396/navigation/UM/flowlines?distance=10&f=json`

## Capture script

`scripts/capture_parity.py` — fetches from Java, processes, writes fixtures.

Responsibilities:
- Fetch each endpoint from the Java base URL
- Tier 1: null out geometry fields, write full response
- Tier 2: build summary dict, write summary
- Record capture timestamp in each fixture
- Document each endpoint and its tier in the script

Usage: `uv run python scripts/capture_parity.py`

Re-run when Java service changes or DB is re-crawled.

## Parity test structure

```
tests/parity/
  conftest.py       — load fixtures, URL normalization, summary builder
  fixtures/         — golden files (JSON)
  test_parity.py    — parametrized tests
```

### conftest.py

- `JAVA_BASE` / `PY_BASE` — for URL normalization
- `normalize_urls(obj, old_base, new_base)` — recursive replace
- `strip_geometry(obj)` — null out geometry fields
- `summarize_collection(body)` — build tier 2 summary from a response
- `load_fixture(name)` — read from fixtures/

### test_parity.py

Tier 1 tests:
- Load golden file
- Hit our app, strip geometry, normalize URLs
- Compare dicts (assertEqual or deepdiff)

Tier 2 tests:
- Load summary golden file
- Hit our app, build summary
- Compare: property_keys exact match, geometry_types exact match
- feature_count within tolerance (±10% or ±5, whichever is greater)
- first_feature property keys match

## Known differences to handle

- **Base URLs** — normalize before comparison
- **comid type** — we return int, Java returns string. Normalize to string.
- **Feature ordering** — collections may differ in order. Sort by identifier.
- **`excludeGeometry`** — our addition, not in Java. Not tested in parity.
- **`/lookups` endpoints** — deprecated, not ported. No parity test.
- **Navigation link URLs** — structure should match, base differs.

## Taskfile target

```yaml
test:parity:
  desc: Run parity tests (requires running app — task dev)
  cmds:
    - uv run pytest tests/parity -m parity -v
```

## Acceptance criteria

- Capture script is self-documenting (comments explain each endpoint and tier)
- All tier 1 golden files match after URL/type normalization
- All tier 2 summaries match on structure; counts within tolerance
- Tests are marked `@pytest.mark.parity`
- Tests require a running local app (same as system tests)
