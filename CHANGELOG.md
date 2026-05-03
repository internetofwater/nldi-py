# Changelog

## Unreleased

### Changed

- Basin queries (`/basin` endpoint) now use `characteristic_data` schema tables
  (`plusflowlinevaa_np21`, `catchmentsp`) instead of `nhdplus` schema, resolving
  timeout issues on large upstream networks (#202).
