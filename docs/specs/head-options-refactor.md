# Spec — Consolidate HEAD handling and fix OPTIONS Allow header

## Problem

The NLDI service supports HEAD on every published GET endpoint. Today this is implemented with a separate `@head(paths, include_in_schema=False)` no-op handler in each of the four controllers (`RootController`, `LookupController`, `NavigationController`, `BasinController`). The pattern works, but it has two costs.

**OPTIONS `Allow` header is incomplete.** When a multi-path `@head` decorator covers a path that a single-path `@get` decorator also serves, Litestar 2.21 builds the route's auto-generated OPTIONS handler with a closure over a partial method set. The result: `OPTIONS /api/nldi/linked-data/{source_name}` reports `Allow: HEAD, OPTIONS` rather than `Allow: GET, HEAD, OPTIONS`. The full diagnosis is in PR #207's discussion and the upstream bug report (filed separately by the maintainer).

Browser CORS preflights are unaffected (they read `Access-Control-Allow-Methods`, set explicitly by `headers_middleware_factory`). Strict HTTP clients reading `Allow` see an incomplete list. This is a real, observable contract mismatch with what the service intends to advertise.

**HEAD policy is duplicated.** Each controller declares its own `@head` decorator with a list of path templates. Adding a new endpoint requires updating two places (the GET decorator and the controller's HEAD path list). Forgetting the second update silently drops HEAD support for the new endpoint, which would only surface under specific tests or client behavior.

## Why act

- The OPTIONS `Allow` header is part of the API contract. RFC 9110 expects servers to advertise the methods a resource supports; clients have a reasonable basis to rely on it.
- The current pattern leaves a recurring trip wire — every new endpoint must remember to be added to the controller's HEAD path list, or HEAD support is silently incomplete.
- Consolidating HEAD into a single declarative location reduces the chance of drift and makes future changes (e.g. adding cache-related HEAD semantics) a one-place change rather than a four-place change.
- Project principle #3 ("Explicit over magical") favors a single, visible mechanism for cross-cutting policy over per-controller repetition.

## Done when

1. `OPTIONS` on any registered GET endpoint returns 204 with `Allow` containing at minimum `GET, HEAD, OPTIONS`.
2. `HEAD` on any registered GET endpoint returns the same status the GET would (typically 200, but 301 for redirect endpoints) with an empty body and the standard response headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Cache-Control`, `Vary`) — preserving today's behavior on existing endpoints, and extending HEAD coverage to GET endpoints that lack it today (e.g. legacy redirects).
3. `HEAD` on a path with no registered GET handler returns 404 — preserving today's behavior.
4. The OPTIONS characterization tests added in PR #207 (`tests/unit/test_routes.py`: `test_options_landing_page`, `test_options_linked_data_endpoint`, `test_options_nonexistent_returns_404`) are tightened to assert the full method set in `Allow` for paths that have a GET handler.
5. Existing HEAD tests (`test_head_landing_page`, `test_head_linked_data_stub`, `test_head_nonexistent_returns_404`) pass unchanged.
6. No GET, POST, or other non-HEAD/non-OPTIONS endpoint changes its observable behavior (status code, response body, headers, error semantics).
7. No business logic executes during a HEAD request — no DB queries, no upstream service calls.
8. HEAD support is declared in one place, not per-controller. Adding a new GET endpoint should automatically gain HEAD and correct OPTIONS support without further per-endpoint configuration.

## Constraints

- **Parity floor** (`docs/principles.md` #1). Any client that previously worked against the Java NLDI service or the current Python service must continue to work. Improvements (e.g. corrected `Allow` headers) are acceptable; regressions are not.
- **Explicit over magical** (`docs/principles.md` #3). The mechanism that implements HEAD short-circuiting must be visible at the app-assembly layer, not hidden behind framework conventions.
- **Resource discipline** (`docs/principles.md` #6). HEAD requests must not acquire database connections or call upstream services. The handler body for any GET endpoint must not run when the request method is HEAD.
- **Deferred logic placement.** The fix must not depend on changes to Litestar itself or on a Litestar version upgrade. The upstream bug report tracks the framework-level issue separately; this work proceeds on Litestar 2.21.x as currently pinned.
- **TDD applies.** Per `.kiro/skills/tdd/SKILL.md`, behavior changes require failing tests first. Refactoring existing behavior (e.g. moving HEAD handling) requires characterization tests to protect what works today.

## Accepted behavioral changes

These are intentional and do not violate the parity floor.

- **OPTIONS `Allow` header gains `GET`.** Today's `Allow: HEAD, OPTIONS` becomes `Allow: GET, HEAD, OPTIONS` on affected paths. This is a strictly additive correction.

## Unspecified outcomes

These are not requirements either way; the spec is neutral.

- **Whether HEAD appears in the OpenAPI schema.** The current implementation hides HEAD via `include_in_schema=False`. Whatever mechanism the plan chooses may or may not change this. Both outcomes (HEAD documented alongside GET, or HEAD remaining hidden) are acceptable. If a choice exists in the plan, the plan writer should call it out and pick one with a brief rationale; this spec does not constrain the choice.

## Explicitly out of scope

- The upstream Litestar bug report. Filed separately by the maintainer; not a deliverable of this work.
- Refactoring of any non-HEAD/non-OPTIONS route handler logic. GET handler bodies are not modified except as required by the decorator change.
- Changes to `before_request = check_format`, the existing format-negotiation hook. It continues to operate as it does today.
- Changes to the existing exception handlers, error response format, or RFC 9457 problem-details handling.
- Changes to the OPTIONS characterization tests' structure beyond tightening assertions.
- Pinning to a different Litestar version. Any future fix from upstream is welcome but not required.

## Acceptance criteria — testable form

These will become specific test cases in the plan:

1. `OPTIONS /api/nldi/` → 204; `Allow` contains `GET`, `HEAD`, `OPTIONS`.
2. `OPTIONS /api/nldi/linked-data/wqp` → 204; `Allow` contains `GET`, `HEAD`, `OPTIONS`.
3. `OPTIONS` on a representative endpoint from each controller (root, lookup, navigation, basin) → 204 with `Allow` containing `GET`, `HEAD`, `OPTIONS`.
4. `OPTIONS /api/nldi/nonexistent` → 404.
5. `HEAD /api/nldi/` → 200; empty body; `access-control-allow-origin: *`; `cache-control` set; `vary` set.
6. `HEAD /api/nldi/about/health` → 200; empty body; the endpoint's custom `cache-control: no-cache` is preserved (not overridden by the standard middleware).
7. `HEAD /api/nldi/linked-data/wqp` → 200; empty body.
8. `HEAD /api/nldi/swagger-ui/index.html` → 301; redirect target in `location` header; empty body.
9. `HEAD /api/nldi/nonexistent` → 404.
10. `HEAD` on an endpoint that, on GET, would touch the database or call an upstream service → 200 with empty body, and the relevant repository / client method is *not* invoked. (Verifiable with a mock or call-count assertion in a unit test.)
11. `GET` behavior across the existing test suite is unchanged — no regression in any GET, POST, or non-HEAD/non-OPTIONS endpoint (modulo the OPTIONS-Allow assertions, which are intentionally tightened).

## Risks and how they are mitigated

- **Risk:** The mechanism that intercepts HEAD must not also intercept HEAD requests to paths that have no GET handler (would return 200 instead of 404).
  - **Mitigation:** The mechanism must operate at a layer that runs only after route matching, not before. The plan must verify this with a test against a nonexistent path.
- **Risk:** HEAD response must still receive the standard headers from `headers_middleware_factory`.
  - **Mitigation:** The plan must specify a layering order (or other mechanism) that ensures headers middleware wraps the HEAD short-circuit response. Verifiable by asserting the headers appear on a HEAD response.
- **Risk:** Spec coverage gap — a future controller is added but does not gain HEAD/OPTIONS support.
  - **Mitigation:** The chosen mechanism must apply to *all* controllers automatically, not require per-controller declaration.
- **Risk:** Behavior of `before_request = check_format` interacts with HEAD in some unforeseen way (e.g. validates `f=` on HEAD requests it shouldn't).
  - **Mitigation:** Today, `check_format` already runs on HEAD and rejects bad `f=`. This behavior should be preserved. The plan must verify with a test.

## Open questions for the plan writer

(These are *how* questions, not *what* questions; they belong in the plan, not here. Listed for the plan writer's convenience.)

- Where exactly does the HEAD short-circuit mechanism live (ASGI middleware, lifecycle hook, something else)?
- What is its interaction order with the existing `headers_middleware_factory`, `disconnect_guard_factory`, `timing_middleware_factory`, and `before_request = check_format`?
- Does it remove the four `@head` no-op handlers, the three path-list constants (`_NAV_PATHS`, `_LOOKUP_PATHS`, `_BASIN_PATHS`), and the `@head` import?
- TDD order: which characterization test goes first, which behavioral change is driven by which red test?
- Any tests in `tests/integration/`, `tests/parity/`, `tests/system/` that exercise HEAD and need adjustment?

## Reference material

- `docs/principles.md` — guiding principles, especially #1, #3, #6.
- PR #207 — characterization tests and the change-of-direction comment that documents the OPTIONS bug discovery.
- `.kiro/RULES.md` — non-negotiable rules for the implementer.
- `.kiro/skills/tdd/SKILL.md` — TDD discipline, including the characterization-test exception for refactors.
- `.kiro/skills/workflow/SKILL.md` — branching, MR process, conventional commits, quality gate.
- `src/nldi/asgi.py` — current app assembly, exception handlers, middleware list.
- `src/nldi/middleware.py` — existing explicit middleware pattern.
- `src/nldi/controllers/{root,linked_data/lookups,linked_data/navigation,linked_data/basin}.py` — current `@head` placement.
