# NLDI-py Implementation Notes

Capture decisions and details that aren't principles but will matter when writing code.

## Deprecated endpoints (not porting)

The following Java endpoints are deprecated by project owner decision and will not be
implemented in the Python version:

- `GET /lookups` — list characteristic types
- `GET /lookups/{characteristicType}/characteristics` — list characteristics by type
- `GET /linked-data/{featureSource}/{featureID}/{characteristicType}` — characteristic data for a feature

## Null vs empty string for missing values

Feature properties use `null` (not empty string) for missing values (comid, reachcode, mainstem).
This differs from the Java implementation which uses empty strings in some cases. Follow up with
project owner to confirm this is acceptable.

## pygeoapi test URL

Integration and system tests should use `https://nhgf.dev-wma.chs.usgs.gov/api/nldi/pygeoapi/` as
`NLDI_PYGEOAPI_URL`. This is the dev instance — do not use production pygeoapi for testing.
