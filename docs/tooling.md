# NLDI-py Tooling

## Package management
- **uv** — dependency resolution, virtual environments, project management

## Testing
- **pytest** — test runner, fixtures, markers
- **testcontainers** — integration tests with PostGIS Docker image (ghcr.io)
- **locust** — load testing (replaces manual curl scripts)

## Code quality
- **ruff** — linting and formatting (single tool, replaces flake8/black/isort)
- **ty** — type checking (Astral toolchain; fall back to mypy if SQLAlchemy generics cause issues). Start moderately strict, calibrate based on pain. Type checking should be in CI but not block commits during early refactor phases — too much churn.

## Task runner
- **Taskfile** — standardized commands for dev workflows (test, lint, format, type-check, build, run)

## CI expectations
- `task lint` — ruff check + format check
- `task typecheck` — ty (or mypy)
- `task test:unit` — fast, no I/O
- `task test:integration` — requires Docker
- All must pass before merge
