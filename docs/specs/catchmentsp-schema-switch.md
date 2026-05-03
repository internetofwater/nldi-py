# Spec: Switch basin queries to characteristic_data schema

## Problem

Basin queries (`/basin` endpoint) time out against production RDS. `EXPLAIN
ANALYZE` shows 45-second execution time for large upstream networks (e.g.
Colorado River basin) vs 369ms for the same query against `characteristic_data`.

The basin query uses two tables. Both exist in both schemas with identical
geometry data, but the `nhdplus` versions have structural differences that
cause poor query performance at scale:

- **`plusflowlinevaa_np21`** — `nhdplus` is missing `dnminorhyd` from its `_ut`
  index, causing 105,963 bitmap scan iterations for large networks.
  `characteristic_data` includes it.

- **`catchmentsp`** — `nhdplus` has 7 columns including unused attributes
  (`gridcode`, `sourcefc`, `areasqkm`, `shape_length`, `shape_area`). Wider
  rows increase I/O per page, compounding significantly when `ST_Union`
  aggregates 165,000+ polygons. `characteristic_data.catchmentsp` has only 3
  columns (`ogc_fid`, `featureid`, `the_geom`).

The Java NLDI implementation uses `characteristic_data` for basin queries and
`nhdplus` for navigation queries. The DBA has directed us to do the same.

## Requirements

- **R-1:** Basin queries use `characteristic_data.plusflowlinevaa_np21` for the
  upstream CTE traversal.

- **R-2:** Basin queries use `characteristic_data.catchmentsp` for geometry
  aggregation.

- **R-3:** The ORM model for `characteristic_data.catchmentsp` maps only the 3
  columns present in that table (`ogc_fid`, `featureid`, `the_geom`).

- **R-4:** All navigation queries (DM, DD, UM, UT) continue to use
  `nhdplus.plusflowlinevaa_np21`. No navigation behavior changes.

- **R-5:** The point-in-catchment lookup (`get_by_point`) continues to use
  `nhdplus.catchmentsp`, consistent with the Java implementation.

- **R-6:** No API behavior, response shapes, or error handling changes.

## Non-goals

- Switching navigation CTEs to `characteristic_data`.
- Modifying `nhdplus` indexes.

## Acceptance Criteria

- **AC-1:** A basin request for a large upstream network (e.g. Colorado River
  comid) completes within the proxy timeout.

- **AC-2:** Basin response geometry is correct and unchanged.

- **AC-3:** Navigation endpoints are unaffected.

- **AC-4:** Integration tests pass.
