# NLDI-py Development Workflow

## Branching model

- `main` — current production code. Untouched during refactor.
- `refactor/v3` — integration branch for the refactor. Functions as "main" for all refactor work.
- Feature branches — short-lived, branch from and merge to `refactor/v3`.
- `refactor/v3` merges to `main` when ready for production cutover.

Tag `pre-refactor` marks the snapshot before the refactor began.

## Feature implementation

1. **Decide** — pick an issue or next item from the phased strategy
2. **Plan** — explore, design the approach, get approval before writing code
3. **Branch + PR** — sync and branch from `refactor/v3`, push, open a PR immediately

   ```bash
   git checkout refactor/v3 && git pull
   git checkout -b feature/xyz
   git push -u origin feature/xyz
   gh pr create --base refactor/v3 --title "..."
   ```

4. **Comment the plan** — post the implementation plan as the first comment on the PR
5. **Implement** — do the work; multiple commits are fine
6. **Before each commit**:

   - `task test:unit` — all unit tests pass
   - `task lint` — ruff check passes
   - `task format` — ruff format passes

7. **Before marking ready for review**:
   - `task test:integration` — all integration tests pass
   - `task typecheck` — type checking passes
8. **Summarize** — add a summary comment on the PR describing what was done
9. **Ready for review** — mark the PR as ready
10. **Cleanup** — after merge, delete local branch

   ```bash
   git checkout refactor/v3 && git pull && git branch -D feature/xyz
   ```

## Rules

- **Agents never merge** — a human must review and merge all PRs
- **No amending commits** — prefer new commits to keep history clean and reviewable
- **Unit tests pass on every commit** — no exceptions
- **Integration tests pass before review** — the PR is not ready until they do
- **PR is the single source of truth** — plan, commits, and summary all in one place

## Issue vs PR documentation

- **Issue** = the "what" and "why" — problem description, analysis, decision rationale
- **PR** = the "how" — implementation plan, commits, summary of changes

The PR is the permanent record. Code changes, but the PR persists. It should contain enough context
to re-create the work or debug a regression months later: what was the plan, what was tried, what
was decided, and why. A future reader should not need to ask the author.

Issues persist as the decision log. "Why did we do X?" → check the issue. "How did we do X?" → check the PR.

## Release (post-refactor)

1. Bump `version` in `pyproject.toml`
2. Merge `refactor/v3` → `main`
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push origin vX.Y.Z`
5. Create release on GitHub
