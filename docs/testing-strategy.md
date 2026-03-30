# NLDI-py Testing Strategy

Tests pass before we commit. No exceptions.

## Test layers

### Unit tests
No database, no network. Pure logic.
- Serialization (GeoJSON, JSON-LD, problem+json)
- Content negotiation (`f=` handling, browser redirect logic)
- Middleware behavior (CORS, HEAD, Cache-Control, Vary headers)
- URL building, parameter validation
- Navigation mode validation
- Error formatting (RFC 9457)

Fast. Run on every commit.

### Integration tests
Testcontainers with the custom PostGIS database image (published on ghcr.io). Real SQL against real data.
- Query correctness (source lookups, feature lookups, spatial intersects)
- Navigation CTEs (all four modes, distance limits, trimming)
- Session lifecycle (one connection, released before response)
- Basin computation, drainage area aggregation
- Edge cases (nonexistent comids, invalid sources, empty result sets)

Slower. Run before merge.

### Parity tests
Contract tests that prove the Python service is a safe replacement for the Java service.
- Capture known-good responses from the Java service as golden files
- Run the same requests against the Python app
- Compare response body shape, status codes, content types
- Not byte-for-byte equality — structural equivalence (same keys, same types, same feature counts)

Golden files should be curated carefully — navigation results can be very large. Use short distances and small result sets. The goal is to verify structure and correctness, not to snapshot the entire river network.

These are the tests that answer: "can we switch?"

### System tests (existing)
Tests that run against a live RDS instance. These exist in the current suite but are not clearly separated. They should be marked and isolated so they don't run in CI by default.

## Test organization

```
tests/
  unit/           # no I/O, no containers
  integration/    # testcontainers + ghcr.io DB image
  parity/         # golden-file contract tests
  system/         # live RDS (manual/gated)
  conftest.py     # shared fixtures, markers
```

## Markers

Use pytest markers to control what runs where:
- `@pytest.mark.unit` — default, always runs
- `@pytest.mark.integration` — requires Docker
- `@pytest.mark.parity` — requires golden files
- `@pytest.mark.system` — requires live RDS, never runs in CI automatically

## Migration from existing tests

The current test suite has useful coverage but is not organized by layer. Refactor alongside the app:
- Identify what each existing test actually exercises (unit vs integration vs system)
- Move to the appropriate directory
- Adapt fixtures to the new session/connection setup as it changes
- Don't throw away working tests — relocate and re-mark them
