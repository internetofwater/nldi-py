# NLDI-py Load Testing

## Current state

Load testing is done manually via shell scripts (`tests/load/`) that use parallel curl batches against deployed infrastructure. This works for smoke testing but lacks:
- Controlled ramp-up and sustained load profiles
- Metrics collection (response times, error rates, connection counts)
- Reproducibility across runs
- Correlation with server-side metrics (DB connections, memory)

## Recommendation: Locust

[Locust](https://locust.io/) is Python-native, scriptable, and can model realistic traffic patterns. A basic test plan would translate directly from the existing shell scripts.

### Test scenarios

**Scenario 1: Navigation (heavy path)**
The primary load concern. Exercises DB connection pool, large result sets, streaming.
- `GET /linked-data/comid/{comid}/navigation/DM/flowlines?distance=50&f=json`
- Random COMIDs from a curated worklist (same approach as `coloradoriver.sh`)
- Vary distance parameter to mix light and heavy queries

**Scenario 2: Basin with split catchment (external dependency)**
Exercises DB + pygeoapi call. Sensitive to upstream timeouts.
- `GET /linked-data/{source}/{id}/basin?splitCatchment=true`

**Scenario 3: Simple lookups (baseline)**
Should stay fast under any load. If these degrade, the problem is connection starvation.
- `GET /linked-data` (source list)
- `GET /linked-data/{source}/{id}` (single feature)

**Scenario 4: Mixed traffic**
Weighted combination of all three — roughly matching real usage patterns.

### What to measure

- Response time percentiles (p50, p95, p99)
- Error rate by status code
- Time-to-first-byte on streaming responses
- Server-side: DB connection count, freeable memory, CPU (via CloudWatch or equivalent)

### Load profiles

- **Ramp**: 0 → 50 users over 5 minutes, sustain for 10 minutes
- **Spike**: Sustain 20 users, spike to 100 for 2 minutes, return to 20
- **Soak**: 30 users sustained for 1 hour (looking for leaks)

### When to run

- After Phase 3 (navigation endpoints complete)
- Before and after session lifecycle fix (#154) to measure improvement
- Before any production cutover

### Where to run

- Against staging infrastructure (with CloudFront/proxy in the path) for realistic behavior
- Against local testcontainers for isolated DB-only benchmarking (no network/proxy noise)
