# NLDI-py Framework Decision

## Decision: Litestar

### Rationale

1. **Team familiarity** — the team knows Litestar's patterns.

2. **Dependency injection** — Litestar's DI system handles session lifecycle, service instantiation,
   and configuration cleanly when used as intended. Previous workarounds that bypassed DI (e.g.
   `_get_session_maker`) should be unwound rather than used as evidence against the framework.

3. **DTO layer** — Litestar's DTO mechanism provides a natural enforcement point for Amundsen's Maxim.
   DTOs define the message model (what goes over the wire) separately from the ORM models (data/object
   model). This replaces the current `as_feature()` pattern where ORM models serialize themselves to
   GeoJSON.

### What changes

- Use Litestar's DI properly for session management
- Introduce DTOs as the boundary between ORM models and API responses
- Remove `as_feature()` from ORM models — serialization is the DTO's job
- Drop advanced-alchemy if plain SQLAlchemy + Litestar DI covers our needs
- Set HTTP headers explicitly via middleware rather than relying on Litestar's built-in CORS/cache behavior

### What stays

- Litestar as the ASGI framework
- Route definitions and controller structure
- OpenAPI generation (works well, no reason to change)
