# NLDI-py Guiding Principles

## 1. Parity first

The mission is to replace the Java NLDI service. Existing clients must not break from the switch.

This means:

- Same endpoints, path structure, and query parameters
- Same response body shapes (GeoJSON FeatureCollections, navigation mode URLs, source lists)
- Same status codes for the same error conditions
- Same content types where clients depend on them (e.g. `application/vnd.geo+json` for flowlines and basins)
- HEAD support (Java handles this automatically via Spring Boot)

Parity is a floor, not a ceiling. Where the Java implementation has gaps — missing CORS headers,
no cache directives — we improve rather than replicate the limitation. Improvements must be additive: a
client that worked against the Java service must work unchanged against this one.

## 2. Separate the models

Per [Amundsen's Maxim](https://www.amundsens-maxim.com/):

> "Your data model is not your object model is not your resource model is not your message model."

- The **data model** is the database schema (NHDPlus tables, crawler sources, feature sources).
- The **object model** is how we work with that data in Python (SQLAlchemy ORM classes).
- The **resource model** is what the API exposes (features, flowlines, basins, navigation).
- The **message model** is what goes over the wire (GeoJSON FeatureCollections, JSON-LD graphs).

These should not be coupled. An ORM model should not know how to serialize itself to GeoJSON. A database
column rename should not break the API response. The message format should be the API's decision,
not the database's.

Currently, ORM models have `as_feature()` methods that produce GeoJSON directly — collapsing data,
object, and message models into one. Serialization should be a separate concern, translating between
internal representations and the API contract.

## 3. Explicit over magical

Prefer code that says what it does over code that relies on framework conventions, implicit defaults,
or behind-the-scenes wiring.

- Set HTTP headers (CORS, Cache-Control, Vary, Content-Type) explicitly rather than trusting framework
  middleware to get it right.
- Serialize responses with visible code rather than template engines that obscure the output.
- If behavior depends on a convention (e.g. "the framework adds Vary when it sees an Origin header"),
  make it explicit so it works regardless of what sits between the app and the client.

When something breaks, explicit code is debuggable. Magic requires reading framework source.

## 4. Earn the dependency

Every dependency must justify its presence by what it does that we can't reasonably do ourselves. If we
use 10% of a library, we bias toward replacing that 10% with local code.

Questions to ask before keeping a dependency:

- Are we using it for what it's designed to do, or working around it?
- Does it give us control where we need it, or does it take control away?
- When it breaks or changes, can we fix it quickly?

Fewer dependencies means fewer upgrade surprises, a smaller attack surface, and easier onboarding for
new contributors.

## 5. Fail clearly

Errors are part of the API contract. They should be specific, actionable, and consistently structured.

- Use [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details (`application/problem+json`)
  for all error responses.
- Use precise status codes: a timeout from an upstream service is a 504, not a 500. An invalid parameter
  is a 400 with the valid options listed. A missing resource is a 404 with what was looked for.
- Never silently swallow errors or fall back to defaults. If an input is invalid, reject it.

## 6. Resource discipline

Acquire late, release early. This applies to database connections, memory, and external service calls — but
database connections are the most critical.

- One database connection per request. No redundant checkouts for validation-then-query.
- Close the connection as soon as the data is in hand. Don't hold it open while rendering a response or
  streaming bytes to a slow client.
- Don't hold a database connection while waiting on an external service.
- Be deliberate about result set sizes. If a query can return unbounded rows, enforce a limit or document
  why it doesn't have one.
