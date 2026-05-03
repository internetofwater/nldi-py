## Implementation Plan

**Spec:** docs/specs/catchmentsp-schema-switch.md

### File structure

| File | Responsibility | Change |
|------|---------------|--------|
| `src/nldi/db/models.py` | ORM model definitions | modified — add `CharacteristicDataBaseModel`, `CharacteristicCatchmentModel`, `CharacteristicFlowlineVAAModel` |
| `src/nldi/db/navigation.py` | Navigation and basin CTE builders | modified — `basin_query()` uses `CharacteristicFlowlineVAAModel` |
| `src/nldi/db/repos.py` | Repository classes | modified — `get_drainage_basin()` uses `CharacteristicCatchmentModel` |
| `tests/unit/test_models.py` | Unit tests for ORM models | modified — assert new models target correct schema and columns |
| `tests/unit/test_navigation_query.py` | Unit tests for query builders | modified — assert `basin_query()` targets `characteristic_data` |

### Behavior checklist (TDD order)

1. `CharacteristicCatchmentModel` maps to schema `characteristic_data`, table `catchmentsp`, with exactly columns `ogc_fid`, `featureid`, `the_geom` → `tests/unit/test_models.py`

2. `CharacteristicFlowlineVAAModel` maps to schema `characteristic_data`, table `plusflowlinevaa_np21` → `tests/unit/test_models.py`

3. `basin_query()` compiled SQL references `characteristic_data.plusflowlinevaa_np21` → `tests/unit/test_navigation_query.py`

4. `get_drainage_basin()` compiled SQL references `characteristic_data.catchmentsp` → `tests/unit/test_repos.py`

5. Characterization: `get_by_point()` still references `nhdplus.catchmentsp` (passes immediately — protects existing behavior) → `tests/unit/test_models.py`

6. Characterization: navigation CTEs (DM, DD, UM, UT) still reference `nhdplus.plusflowlinevaa_np21` (passes immediately — protects existing behavior) → `tests/unit/test_navigation_query.py`

### Commit sequence

1. `feat: add CharacteristicDataBaseModel and characteristic_data ORM models`
2. `feat: basin_query uses characteristic_data.plusflowlinevaa_np21`
3. `feat: get_drainage_basin uses characteristic_data.catchmentsp`

### Prerequisites

- `refactor/v3` is the base branch
- `characteristic_data.plusflowlinevaa_np21` and `characteristic_data.catchmentsp` exist on the target RDS instance (confirmed by DBA)
- Integration test container (`ghcr.io/internetofwater/nldi-db:demo`) must have `characteristic_data` schema for integration tests to pass — verify before running `task test:integration`
